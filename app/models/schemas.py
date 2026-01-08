from __future__ import annotations
from enum import Enum
import json
import datetime
from pydantic import BaseModel, field_validator, model_validator
from typing import List, Optional, Union, Iterable
from app.db.utils import log_performance
from app.logging_config import get_logger

logger = get_logger(__name__)


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class CisTrans(Enum):
    cis = "cis"
    trans = "trans"


class StudyDataType(Enum):
    splice_variant = "Splice Variant"
    gene_expression = "Gene Expression"
    methylation = "Methylation"
    protein = "Protein"
    cell_trait = "Cell Trait"
    plasma_protein = "Plasma Protein"
    phenotype = "Phenotype"


class VariantType(Enum):
    common = "Common"
    rare_exome = "Rare Exome"
    rare_wgs = "Rare WGS"


class StudySource(BaseModel):
    id: int
    source: str
    name: str
    url: str
    doi: str


class AssociationMetadata(BaseModel):
    start_snp_id: int
    stop_snp_id: int
    associations_table_name: str


class ColocPairMetadata(BaseModel):
    start_id: int
    stop_id: int
    coloc_pairs_table_name: str


class ColocGroup(BaseModel):
    coloc_group_id: int
    study_id: int
    study_extraction_id: int
    snp_id: int
    ld_block_id: int
    h4_connectedness: float
    h3_connectedness: float
    chr: Optional[int] = None
    bp: Optional[int] = None
    min_p: Optional[float] = None
    cis_trans: Optional[str] = None
    ld_block: Optional[str] = None
    display_snp: str
    rsid: str
    gene: Optional[str] = None
    gene_id: Optional[int] = None
    trait_id: Optional[int] = None
    trait_name: Optional[str] = None
    trait_category: Optional[str] = None
    data_type: Optional[str] = None
    tissue: Optional[str] = None
    cell_type: Optional[str] = None
    source_id: int
    source_name: str
    source_url: str

    @field_validator("data_type")
    def validate_data_type(cls, v):
        return StudyDataType[v].value if enum_has_member(StudyDataType, v) else v


class LdBlock(BaseModel):
    id: int
    chr: int
    start: int
    stop: int
    ancestry: str
    ld_block: str


class Ld(BaseModel):
    lead_snp_id: int
    variant_snp_id: int
    ld_block_id: int
    r: float


class Lds(BaseModel):
    lds: List[Ld]


class Gene(BaseModel):
    id: int
    ensembl_id: str
    gene: str
    description: Optional[str] = None
    gene_biotype: Optional[str] = None
    chr: int
    start: int
    stop: int
    strand: int
    source: Optional[str] = None
    distinct_trait_categories: Optional[int] = None
    distinct_protein_coding_genes: Optional[int] = None
    genes_in_region: Optional[List[Gene]] = None


class ExtendedGene(Gene):
    num_study_extractions: Optional[int] = None
    num_coloc_groups: Optional[int] = None
    num_coloc_studies: Optional[int] = None
    num_rare_results: Optional[int] = None


class GeneMetadata(BaseModel):
    symbol: str
    chr: int
    min_bp: int
    max_bp: int


class ExtendedColocGroup(ColocGroup):
    association: Optional[dict] = None  # allow raw dict rows to avoid overhead


class Trait(BaseModel):
    id: int
    data_type: str
    trait: str
    trait_name: str
    trait_category: Optional[str] = None
    common_study: Optional[Study] = None
    rare_study: Optional[Study] = None

    @field_validator("data_type")
    def validate_data_type(cls, v):
        return StudyDataType[v].value if enum_has_member(StudyDataType, v) else v


class BasicTraitResponse(BaseModel):
    id: int
    data_type: str
    trait: str
    trait_name: str
    trait_category: Optional[str] = None
    variant_type: str
    sample_size: int
    category: str
    ancestry: str
    heritability: Optional[float] = None
    heritability_se: Optional[float] = None
    num_study_extractions: int
    num_coloc_groups: int
    num_coloc_studies: int
    num_rare_results: int

    @field_validator("data_type")
    def validate_data_type(cls, v):
        return StudyDataType[v].value if enum_has_member(StudyDataType, v) else v

    @field_validator("variant_type")
    def validate_variant_type(cls, v):
        return VariantType[v].value if enum_has_member(VariantType, v) else v


class GetTraitsResponse(BaseModel):
    traits: List[BasicTraitResponse]


class GenePleiotropy(BaseModel):
    gene_id: int
    gene: str
    distinct_trait_categories: int
    distinct_protein_coding_genes: int


class SnpPleiotropy(BaseModel):
    snp_id: int
    display_snp: str
    distinct_trait_categories: int
    distinct_protein_coding_genes: int


class GenePleiotropyResponse(BaseModel):
    genes: List[GenePleiotropy]


class SnpPleiotropyResponse(BaseModel):
    snps: List[SnpPleiotropy]


class GetStudySourcesResponse(BaseModel):
    sources: List[StudySource]


class Study(BaseModel):
    id: int
    data_type: str
    study_name: str
    trait_id: int
    ancestry: Optional[str] = None
    sample_size: Optional[int] = None
    category: Optional[str] = None
    probe: Optional[str] = None
    tissue: Optional[str] = None
    cell_type: Optional[str] = None
    source_id: Optional[int] = None
    variant_type: Optional[str] = None
    p_value_threshold: float
    gene_id: Optional[int] = None
    gene: Optional[str] = None
    ensg: Optional[str] = None
    heritability: Optional[float] = None
    heritability_se: Optional[float] = None

    @field_validator("data_type")
    def validate_data_type(cls, v):
        return StudyDataType[v].value if enum_has_member(StudyDataType, v) else v

    @field_validator("variant_type")
    def validate_variant_type(cls, v):
        return VariantType[v].value if enum_has_member(VariantType, v) else v


class StudyExtraction(BaseModel):
    id: int
    study_id: int
    snp_id: int
    display_snp: str
    rsid: str
    ld_block_id: int
    unique_study_id: str
    study: str
    file: str
    svg_file: Optional[str] = None
    file_with_lbfs: Optional[str] = None
    chr: int
    bp: int
    min_p: float
    cis_trans: Optional[str] = None
    ld_block: str
    gene_id: Optional[int] = None
    situated_gene_id: Optional[int] = None


class ExtendedStudyExtraction(StudyExtraction):
    gene: Optional[str] = None
    trait_id: int
    trait_name: str
    trait_category: Optional[str] = None
    data_type: str
    tissue: Optional[str] = None
    cell_type: Optional[str] = None

    @field_validator("data_type")
    def validate_data_type(cls, v):
        return StudyDataType[v].value if enum_has_member(StudyDataType, v) else v


class SearchTerm(BaseModel):
    type: str
    name: Optional[str] = None
    alt_name: Optional[str] = None
    type_id: Optional[int | str] = None
    sample_size: Optional[int] = None
    num_study_extractions: Optional[int] = None
    num_coloc_groups: Optional[int] = None
    num_coloc_studies: Optional[int] = None
    num_rare_results: Optional[int] = None


class SearchTerms(BaseModel):
    search_terms: List[SearchTerm]


class RareResult(BaseModel):
    rare_result_group_id: int
    study_id: int
    study_extraction_id: int
    snp_id: int
    gene_id: Optional[int] = None
    situated_gene_id: Optional[int] = None
    ld_block_id: int
    chr: int
    bp: int
    min_p: float
    cis_trans: Optional[str] = None
    display_snp: str
    rsid: str
    gene: Optional[str] = None
    situated_gene: Optional[str] = None
    trait_id: Optional[int] = None
    trait_name: Optional[str] = None
    trait_category: Optional[str] = None
    data_type: Optional[str] = None
    tissue: Optional[str] = None
    cell_type: Optional[str] = None
    ld_block: Optional[str] = None
    source_id: Optional[int] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None

    @field_validator("data_type")
    def validate_data_type(cls, v):
        return StudyDataType[v].value if enum_has_member(StudyDataType, v) else v


class ExtendedRareResult(RareResult):
    association: Optional[dict] = None  # allow raw dict rows to avoid overhead


class Variant(BaseModel):
    id: int
    snp: str
    display_snp: str
    chr: int
    bp: int
    ea: str
    oa: str
    ref_allele: str
    flipped: bool
    gene_id: Optional[int] = None
    gene: str
    feature_type: str
    consequence: Optional[str] = None
    cdna_position: Optional[str] = None
    cds_position: Optional[str] = None
    protein_position: Optional[str] = None
    amino_acids: Optional[str] = None
    codons: Optional[str] = None
    rsid: Optional[str] = None
    impact: Optional[str] = None
    symbol: Optional[str] = None
    biotype: Optional[str] = None
    strand: Optional[int] = None
    canonical: Optional[str] = None
    all_af: Optional[float] = None
    eur_af: Optional[float] = None
    eas_af: Optional[float] = None
    amr_af: Optional[float] = None
    afr_af: Optional[float] = None
    sas_af: Optional[float] = None
    distinct_trait_categories: Optional[int] = None
    distinct_protein_coding_genes: Optional[int] = None
    associations: Optional[List[dict]] = None  # allow raw dict rows to avoid overhead


class ExtendedVariant(Variant):
    num_colocs: Optional[int] = None
    coloc_groups: Optional[List[ColocGroup]] = None
    num_rare_results: Optional[int] = None
    rare_results: Optional[List[RareResult]] = None
    ld_proxies: Optional[List[Ld]] = None


class GetGenesResponse(BaseModel):
    genes: List[ExtendedGene]


class GeneResponse(BaseModel):
    gene: Gene
    coloc_groups: List[ColocGroup]
    coloc_pairs: Optional[List[dict]] = None  # allow raw dict rows to avoid overhead
    rare_results: List[RareResult]
    variants: List[Variant]
    study_extractions: List[ExtendedStudyExtraction]
    tissues: List[str]
    associations: Optional[List[dict]] = None  # allow raw dict rows to avoid overhead


class RegionResponse(BaseModel):
    region: LdBlock
    genes_in_region: List[Gene]
    coloc_groups: List[ColocGroup]
    rare_results: List[RareResult]
    variants: List[Variant]
    tissues: List[str]


class VariantResponse(BaseModel):
    variant: Variant
    coloc_groups: List[ExtendedColocGroup]
    coloc_pairs: Optional[List[dict]] = None  # allow raw dict rows to avoid overhead
    rare_results: List[ExtendedRareResult]
    study_extractions: List[ExtendedStudyExtraction]
    associations: Optional[List[dict]] = None  # allow raw dict rows to avoid overhead


class VariantSummaryStatsResponse(BaseModel):
    variant: Variant


class VariantSearchResponse(BaseModel):
    original_variants: List[ExtendedVariant]
    proxy_variants: List[ExtendedVariant]


class TraitResponse(BaseModel):
    trait: Trait | GwasUpload
    coloc_groups: Optional[List[ColocGroup]] | Optional[List[ExtendedUploadColocGroup]] = None
    rare_results: Optional[List[RareResult]] = None
    study_extractions: Optional[List[ExtendedStudyExtraction]] = None
    upload_study_extractions: Optional[List[UploadStudyExtraction]] = None
    associations: Optional[List[dict]] = None  # allow raw dict rows to avoid overhead


class UploadTraitResponse(BaseModel):
    trait: Trait | GwasUpload
    coloc_groups: Optional[List[ExtendedUploadColocGroup]] = None
    coloc_pairs: Optional[List[UploadColocPair]] = None
    study_extractions: Optional[List[ExtendedStudyExtraction]] = None
    upload_study_extractions: Optional[List[UploadStudyExtraction]] = None
    associations: Optional[List[dict]] = None  # allow raw dict rows to avoid overhead


class GwasStatus(Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ContactRequest(BaseModel):
    email: str
    reason: str
    message: str


class ProcessGwasRequest(BaseModel):
    guid: Optional[str] = None
    reference_build: str
    email: str
    name: str
    category: str
    is_published: bool
    doi: Optional[str] = None
    should_be_added: bool
    ancestry: str
    sample_size: int
    p_value_threshold: float
    column_names: GwasColumnNames
    status: Optional[GwasStatus] = None

    @model_validator(mode="before")
    @classmethod
    def to_py_dict(cls, data):
        return json.loads(data)


class UpdateGwasRequest(BaseModel):
    success: bool
    failure_reason: Optional[str] = None
    coloc_pairs: Optional[List[UpdateGwasColocPair]] = None
    coloc_groups: Optional[List[UpdateGwasColocGroup]] = None
    study_extractions: Optional[List[UpdateGwasStudyExtraction]] = None


class UpdateGwasColocPair(BaseModel):
    unique_study_id_a: str
    unique_study_id_b: str
    h3: float
    h4: float
    ld_block: str
    false_positive: bool
    false_negative: bool
    ignore: bool


class UpdateGwasColocGroup(BaseModel):
    coloc_group_id: int
    unique_study_id: str
    snp: str
    ld_block: str
    h4_connectedness: float
    h3_connectedness: float


class UpdateGwasStudyExtraction(BaseModel):
    study: str
    unique_study_id: str
    snp: str
    file: str
    chr: int
    bp: int
    min_p: float
    ld_block: str


class GwasColumnNames(BaseModel):
    SNP: Optional[str] = None
    RSID: Optional[str] = None
    CHR: Optional[str] = None
    BP: Optional[str] = None
    EA: Optional[str] = None
    OA: Optional[str] = None
    P: Optional[str] = None
    BETA: Optional[str] = None
    OR: Optional[str] = None
    LB: Optional[str] = None
    UB: Optional[str] = None
    SE: Optional[str] = None
    EAF: Optional[str] = None


class GwasState(BaseModel):
    guid: str
    state: Optional[GwasStatus] = None
    message: Optional[str] = None


class GwasUpload(BaseModel):
    id: int
    guid: Optional[str] = None
    email: str
    name: str
    sample_size: int
    ancestry: str
    category: str
    is_published: bool
    doi: str
    should_be_added: bool
    status: GwasStatus
    failure_reason: Optional[str] = None
    created_at: Optional[datetime.datetime] = None


GwasUpload.model_rebuild()


class UploadStudyExtraction(BaseModel):
    id: Optional[int] = None
    gwas_upload_id: Optional[int] = None
    snp_id: Optional[int] = None
    snp: Optional[str] = None
    ld_block_id: Optional[int] = None
    unique_study_id: Optional[str] = None
    study: Optional[str] = None
    file: Optional[str] = None
    chr: Optional[int] = None
    bp: Optional[int] = None
    min_p: Optional[float] = None
    ld_block: Optional[str] = None

    model_config = {"from_attributes": True}


class UploadColocGroup(BaseModel):
    gwas_upload_id: int
    coloc_group_id: int
    existing_study_extraction_id: Optional[int] = None
    study_extraction_id: Optional[int] = None
    snp_id: int
    ld_block_id: int
    h4_connectedness: float
    h3_connectedness: float

    model_config = {"from_attributes": True}


class UploadColocPair(BaseModel):
    gwas_upload_id: Optional[int] = None
    existing_study_extraction_id_a: Optional[int] = None
    study_extraction_id_a: Optional[int] = None
    existing_study_extraction_id_b: Optional[int] = None
    study_extraction_id_b: Optional[int] = None
    ld_block_id: int
    h3: float
    h4: float
    false_positive: bool
    false_negative: bool
    ignore: bool


class ExtendedUploadColocGroup(UploadColocGroup):
    trait_name: Optional[str] = None
    trait_category: Optional[str] = None
    data_type: Optional[str] = None
    tissue: Optional[str] = None
    cis_trans: Optional[str] = None

    @field_validator("data_type")
    def validate_data_type(cls, v):
        return StudyDataType[v].value if enum_has_member(StudyDataType, v) else v


class GPMapMetadata(BaseModel):
    num_common_studies: int
    num_rare_studies: int
    num_molecular_studies: int
    num_coloc_groups: int
    num_causal_variants: int


@log_performance
def convert_duckdb_to_pydantic_model(
    model: BaseModel, results: Union[List[tuple], tuple]
) -> Union[List[BaseModel], BaseModel]:
    """Convert DuckDB query results to a Pydantic model instance"""
    if isinstance(results, list):
        converted = []
        if len(results) == 0:
            return []
        else:
            for row in results:
                if row and not all(v is None for v in row):
                    model_dict = {
                        field: row[idx] for idx, field in enumerate(model.model_fields.keys()) if idx < len(row)
                    }
                    converted.append(model(**model_dict))
                else:
                    converted.append(None)
        return converted

    # Handle single tuple case
    elif isinstance(results, tuple):
        if results and not all(v is None for v in results):
            return model(
                **{field: results[idx] for idx, field in enumerate(model.model_fields.keys()) if idx < len(results)}
            )
        return None
    else:
        raise ValueError("Results must be a list of tuples or a single tuple.")


@log_performance
def convert_duckdb_tuples_to_dicts(
    rows: Union[List[tuple], tuple],
    columns: List[str],
    as_generator: bool = False,
) -> Union[List[dict], Iterable[dict]]:
    if rows is None or not columns:
        return [] if not as_generator else iter(())

    if isinstance(rows, tuple):
        rows = (rows,)

    cols = columns
    mapped = (dict(zip(cols, r)) for r in rows if r is not None)
    return mapped if as_generator else list(mapped)


def enum_has_member(enum_class, key: str) -> bool:
    try:
        return key in enum_class.__members__
    except Exception:
        return False
