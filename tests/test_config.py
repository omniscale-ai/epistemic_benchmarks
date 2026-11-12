from abductbench.config import (
    Family,
    Stage,
    Truth,
    VariantConfig,
    all_variants,
    pair_id_of,
)


def test_variant_id_unique_across_all_variants():
    variants = all_variants()
    ids = [v.variant_id for v in variants]
    assert len(set(ids)) == len(ids)
    assert len(ids) == 4 * 4 * 5 * 2 == 160


def test_pair_id_groups_entity_and_no_entity():
    entity = VariantConfig(family=Family.BETA, truth=Truth.ENTITY, stage=Stage.HISTORICAL, seed=0, mode=1)
    no_entity = VariantConfig(family=Family.BETA, truth=Truth.NO_ENTITY, stage=Stage.HISTORICAL, seed=0, mode=1)
    assert entity.pair_id == no_entity.pair_id
    assert entity.variant_id != no_entity.variant_id


def test_pair_id_of_drops_truth_segment():
    assert pair_id_of("beta-entity-a-s0-m1") == "beta-a-s0-m1"


def test_pair_id_of_matches_pair_id_for_all_variants():
    for cfg in all_variants():
        assert pair_id_of(cfg.variant_id) == cfg.pair_id
