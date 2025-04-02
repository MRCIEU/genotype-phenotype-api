from __future__ import annotations
from enum import Enum
import json
from pydantic import BaseModel, model_validator
from typing import ForwardRef, List, Optional, Union, Any

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class StudySource(BaseModel):
    id: int
    name: str
    source: str
    url: str
    doi: str

class Association(BaseModel):
    snp_id: int
    study_id: int
    beta: float
    se: float
    imputed: bool
    p: float
    eaf: float

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
    known_gene: Optional[str] = None
    trait: Optional[str] = None
    data_type: Optional[str] = None
    tissue: Optional[str] = None

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
    symbol: str
    chr: int 
    min_bp: int
    max_bp: int
    genes_in_region: Optional[List[Gene]] = None

class GeneMetadata(BaseModel):
    symbol: str
    chr: int 
    min_bp: int
    max_bp: int

class ExtendedColoc(Coloc):
    association: Optional[Association] = None

class Study(BaseModel):
    id: int
    data_type: str
    data_format: str
    study_name: str
    trait: str
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
    known_gene: Optional[str] = None
    trait: str
    data_type: str
    tissue: Optional[str] = None

class SearchTerm(BaseModel):
    type: str
    name: Optional[str] = None
    type_id: Optional[int | str] = None

class RareSNPGroups(BaseModel):
    rare_result_group_id: int
    study_id: int
    study_extraction_id: int
    ld_block_id: int
    snp_id: int
    unique_study_id: str
    candidate_snp: str
    study: str
    chr: int
    bp: int
    min_p: float
    cis_trans: Optional[str] = None
    known_gene: Optional[str] = None

class Variant(BaseModel):
    id: int
    snp: str
    chr: int
    bp: int
    ea: str
    oa: str
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


class GeneResponse(BaseModel):
    gene: Gene
    colocs: List[Coloc]
    variants: List[Variant]
    study_extractions: List[StudyExtraction]
    tissues: List[str]

class Region(BaseModel):
    ancestry: str
    chr: int 
    start: int
    end: int

class RegionResponse(BaseModel):
    region: Region
    colocs: List[Coloc]
    genes: List[GeneMetadata] 

class VariantResponse(BaseModel):
    variant: Variant
    colocs: List[ExtendedColoc]

class StudyResponse(BaseModel):
    study: Study
    colocs: List[Coloc]
    study_extractions: List[StudyExtraction]

class GwasStatus(Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ProcessGwasRequest(BaseModel):
    file: Optional[str] = None
    file_hash: Optional[str] = None
    trait_name: Optional[str] = None
    study_type: Optional[str] = None
    reference_build: Optional[str] = None
    email: Optional[str] = None
    is_published: Optional[bool] = None
    doi: Optional[str] = None
    permanent: Optional[bool] = None
    ancestry: Optional[str] = None
    sample_size: Optional[int] = None
    column_names: Optional[GwasColumnNames] = None

    @model_validator(mode="before")
    @classmethod
    def to_py_dict(cls, data):
        return json.loads(data)

class GwasColumnNames(BaseModel):
    snp: Optional[str] = None
    rsid: Optional[str] = None
    chr: Optional[str] = None
    bp: Optional[str] = None
    ea: Optional[str] = None
    oa: Optional[str] = None
    p: Optional[str] = None
    beta: Optional[str] = None
    odds_ratio: Optional[str] = None
    se: Optional[str] = None
    eaf: Optional[str] = None

class GwasState(BaseModel):
    guid: str
    state: Optional[GwasStatus] = None
    message: Optional[str] = None

class GwasUpload(BaseModel):
    guid: str
    name: str
    sample_size: int
    p_value_threshold: float
    ancestry: str
    category: str
    is_published: bool
    doi: str
    permanent: bool
    status: GwasStatus

def convert_duckdb_to_pydantic_model(model: BaseModel, results: Union[List[tuple], tuple]) -> Union[List[BaseModel], BaseModel]:
    """Convert DuckDB query results to a Pydantic model instance"""
    if isinstance(results, list):
        if len(results) == 0: return []
        return [model(**{
            field: row[idx] for idx, field in enumerate(model.model_fields.keys())
            if idx < len(row)  # Only include fields that exist in the tuple
        }) for row in results]
    elif isinstance(results, tuple):
        return model(**{
            field: results[idx] for idx, field in enumerate(model.model_fields.keys())
            if idx < len(results)  # Only include fields that exist in the tuple
        })
    else:
        raise ValueError("Results must be a list of tuples or a single tuple.")

