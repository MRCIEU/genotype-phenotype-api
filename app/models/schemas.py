from __future__ import annotations
from enum import Enum
import json
from pydantic import BaseModel, field_validator, model_validator
from typing import List, Optional, Union

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class StudyDataType(Enum):
    splice_variant = "Splice Variant"
    gene_expression = "Gene Expression"
    methylation = "Methylation"
    protein = "Protein"
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

class Association(BaseModel):
    snp_id: int
    study_id: int
    beta: float
    se: float
    p: float
    eaf: float
    imputed: bool

class Coloc(BaseModel):
    study_extraction_id: int
    snp_id: int
    ld_block_id: int
    coloc_group_id: int
    iteration: int
    unique_study_id: str
    posterior_prob: float
    regional_prob: float
    posterior_explained_by_snp: float
    candidate_snp: str
    study_id: int
    chr: Optional[int] = None
    bp: Optional[int] = None
    min_p: Optional[float] = None
    cis_trans: Optional[str] = None
    ld_block: Optional[str] = None
    gene: Optional[str] = None
    gene_id: Optional[int] = None
    trait_id: Optional[int] = None
    trait_name: Optional[str] = None
    trait_category: Optional[str] = None
    data_type: Optional[str] = None
    tissue: Optional[str] = None

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
    genes_in_region: Optional[List[Gene]] = None

class GeneMetadata(BaseModel):
    symbol: str
    chr: int 
    min_bp: int
    max_bp: int

class ExtendedColoc(Coloc):
    association: Optional[Association] = None

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

    @field_validator("data_type")
    def validate_data_type(cls, v):
        return StudyDataType[v].value if enum_has_member(StudyDataType, v) else v

    @field_validator("variant_type")
    def validate_variant_type(cls, v):
        return VariantType[v].value if enum_has_member(VariantType, v) else v

class GetTraitsResponse(BaseModel):
    traits: List[BasicTraitResponse]

class GetStudySourcesResponse(BaseModel):
    sources: List[StudySource]

class Study(BaseModel):
    id: int
    data_type: str
    data_format: str
    study_name: str
    trait_id: int
    ancestry: Optional[str] = None
    sample_size: Optional[int] = None
    category: Optional[str] = None
    study_location: str
    extracted_location: str
    probe: Optional[str] = None
    tissue: Optional[str] = None
    source_id: Optional[int] = None
    variant_type: Optional[str] = None
    p_value_threshold: float
    gene: Optional[str] = None
    gene_id: Optional[int] = None

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
    snp: str
    ld_block_id: int
    unique_study_id: str
    study: str
    file: str
    chr: int 
    bp: int
    min_p: float
    cis_trans: Optional[str] = None
    ld_block: str
    gene: Optional[str] = None
    gene_id: Optional[int] = None
    trait_id: Optional[int] = None

class ExtendedStudyExtraction(StudyExtraction):
    trait_name: str
    trait_category: Optional[str] = None
    data_type: str
    tissue: Optional[str] = None

    @field_validator("data_type")
    def validate_data_type(cls, v):
        return StudyDataType[v].value if enum_has_member(StudyDataType, v) else v

class SearchTerm(BaseModel):
    type: str
    name: Optional[str] = None
    type_id: Optional[int | str] = None

class RareResult(BaseModel):
    rare_result_group_id: int
    study_extraction_id: int
    snp_id: int
    ld_block_id: int
    unique_study_id: str
    candidate_snp: str
    study_id: int
    file: str
    chr: int
    bp: int
    min_p: float
    gene: Optional[str] = None
    gene_id: Optional[int] = None
    trait_id: Optional[int] = None
    trait_name: Optional[str] = None
    trait_category: Optional[str] = None
    data_type: Optional[str] = None
    tissue: Optional[str] = None
    ld_block: Optional[str] = None

    @field_validator("data_type")
    def validate_data_type(cls, v):
        return StudyDataType[v].value if enum_has_member(StudyDataType, v) else v

class ExtendedRareResult(RareResult):
    association: Optional[Association] = None

class Variant(BaseModel):
    id: int
    snp: str
    chr: int
    bp: int
    ea: str
    oa: str
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
    associations: Optional[List[Association]] = None

class ExtendedVariant(Variant):
    num_colocs: Optional[int] = None
    num_rare_variants: Optional[int] = None
    ld_proxies: Optional[List[Ld]] = None

class GetGenesResponse(BaseModel):
    genes: List[Gene]

class GeneResponse(BaseModel):
    gene: Gene
    colocs: List[Coloc]
    rare_results: List[RareResult]
    variants: List[Variant]
    study_extractions: List[ExtendedStudyExtraction]
    tissues: List[str]

class Region(BaseModel):
    ancestry: str
    chr: int 
    start: int
    end: int

class RegionResponse(BaseModel):
    region: Region
    colocs: List[Coloc]
    genes: List[Gene] 

class VariantResponse(BaseModel):
    variant: Variant
    colocs: List[ExtendedColoc]
    rare_results: List[ExtendedRareResult]

class VariantSearchResponse(BaseModel):
    original_variants: List[ExtendedVariant]
    proxy_variants: List[ExtendedVariant]

class TraitResponse(BaseModel):
    trait: Trait | GwasUpload
    colocs: Optional[List[Coloc]] | Optional[List[ExtendedUploadColoc]] = None
    rare_results: Optional[List[RareResult]] = None
    study_extractions: Optional[List[ExtendedStudyExtraction]] = None
    upload_study_extractions: Optional[List[UploadStudyExtraction]] = None
    associations: Optional[List[Association]] = None

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
    column_names: GwasColumnNames
    status: Optional[GwasStatus] = None

    @model_validator(mode="before")
    @classmethod
    def to_py_dict(cls, data):
        return json.loads(data)

class UpdateGwasRequest(BaseModel):
    success: bool
    failure_reason: Optional[str] = None
    coloc_results: Optional[List[UploadColoc]] = None
    study_extractions: Optional[List[UploadStudyExtraction]] = None

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
    cis_trans: Optional[str] = None
    ld_block: Optional[str] = None
    gene: Optional[str] = None

    model_config = {
        "from_attributes": True
    }


class UploadColoc(BaseModel):
    gwas_upload_id: Optional[int] = None
    upload_study_extraction_id: Optional[int] = None
    existing_study_extraction_id: Optional[int] = None
    snp_id: Optional[int] = None
    ld_block_id: Optional[int] = None
    coloc_group_id: Optional[int] = None
    iteration: Optional[int] = None
    unique_study_id: Optional[str] = None
    posterior_prob: Optional[float] = None
    regional_prob: Optional[float] = None
    posterior_explained_by_snp: Optional[float] = None
    candidate_snp: Optional[str] = None
    study_id: Optional[int] = None
    chr: Optional[int] = None
    bp: Optional[int] = None
    min_p: Optional[float] = None
    cis_trans: Optional[str] = None
    ld_block: Optional[str] = None
    gene: Optional[str] = None
    gene_id: Optional[int] = None

    model_config = {
        "from_attributes": True
    }

class ExtendedUploadColoc(UploadColoc):
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
    

def convert_duckdb_to_pydantic_model(model: BaseModel, results: Union[List[tuple], tuple]) -> Union[List[BaseModel], BaseModel]:
    """Convert DuckDB query results to a Pydantic model instance"""
    if isinstance(results, list):
        if len(results) == 0: return []
        converted = []
        for row in results:
            if row and not all(v is None for v in row):
                model_dict = {
                    field: row[idx] 
                    for idx, field in enumerate(model.model_fields.keys())
                    if idx < len(row)
                }
                converted.append(model(**model_dict))
            else:
                converted.append(None)
        return converted

    # Handle single tuple case
    elif isinstance(results, tuple):
        if results and not all(v is None for v in results):
            return model(**{
                field: results[idx] 
                for idx, field in enumerate(model.model_fields.keys())
                if idx < len(results)
            })
        return None
    else:
        raise ValueError("Results must be a list of tuples or a single tuple.")

def enum_has_member(enum_class, key: str) -> bool:
    return key in enum_class.__members__

