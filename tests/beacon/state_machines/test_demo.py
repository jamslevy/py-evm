import pytest


from eth._utils import bls as bls
from eth.beacon.db.chain import BeaconChainDB
from eth.beacon.enums import (
    SignatureDomain,
)
from eth.beacon.helpers import (
    get_beacon_proposer_index,
)
from eth.beacon.state_machines.forks.serenity.blocks import (
    SerenityBeaconBlock,
)


from eth.beacon.types.proposal_signed_data import ProposalSignedData


@pytest.mark.parametrize(
    (
        'num_validators,'
        'epoch_length,'
        'min_attestation_inclusion_delay,'
        'target_committee_size,'
        'shard_count'
    ),
    [
        (10, 2, 1, 2, 2)
    ]
)
def test_demo(base_db,
              sample_beacon_block_params,
              genesis_state,
              fixture_sm_class,
              config,
              privkeys,
              pubkeys):
    chaindb = BeaconChainDB(base_db, SerenityBeaconBlock)
    state = genesis_state
    block = SerenityBeaconBlock(**sample_beacon_block_params).copy(
        slot=state.slot + 2,
        state_root=state.root,
    )

    # Sign block
    beacon_proposer_index = get_beacon_proposer_index(
        # TODO: use `state` when the bug of `get_shard_committees_at_slot` is fixed.
        state.copy(
            slot=state.slot + 2,
        ),
        block.slot,
        config.EPOCH_LENGTH,
    )
    index_in_privkeys = pubkeys.index(
        state.validator_registry[beacon_proposer_index].pubkey
    )
    beacon_proposer_privkey = privkeys[index_in_privkeys]
    empty_signature_block_root = block.block_without_signature_root
    proposal_root = ProposalSignedData(
        block.slot,
        config.BEACON_CHAIN_SHARD_NUMBER,
        empty_signature_block_root,
    ).root
    block = block.copy(
        signature=bls.sign(
            message=proposal_root,
            privkey=beacon_proposer_privkey,
            domain=SignatureDomain.DOMAIN_PROPOSAL,
        ),
    )

    # Store in chaindb
    chaindb.persist_block(block)
    chaindb.persist_state(state)

    # Get state machine instance
    sm = fixture_sm_class(chaindb, block.root)
    result_state, _ = sm.import_block(block)

    assert state.slot == 0
    assert result_state.slot == block.slot
    assert isinstance(sm.block, SerenityBeaconBlock)
