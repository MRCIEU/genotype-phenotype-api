from pydantic import BaseModel
from typing import List, Optional, Union, Any

class Association(BaseModel):
    SNP: Optional[str] = None
    BETA: Optional[float] = None
    SE: Optional[float] = None
    IMPUTED: Optional[bool] = None
    P: Optional[float] = None
    EAF: Optional[float] = None
    study: Optional[str] = None

class Coloc(BaseModel):
    iteration: Optional[int] = None
    traits: Optional[str] = None
    posterior_prob: Optional[float] = None
    regional_prob: Optional[float] = None
    candidate_snp: Optional[str] = None
    posterior_explained_by_snp: Optional[float] = None
    dropped_trait: Optional[bool] = None
    id: Optional[int] = None
    study: Optional[str] = None
    chr: Optional[int] = None
    bp: Optional[int] = None
    min_p: Optional[float] = None
    cis_trans: Optional[str] = None
    ld_block: Optional[str] = None
    known_gene: Optional[str] = None
    file: Optional[str] = None
    trait: Optional[str] = None
    data_type: Optional[str] = None
    tissue: Optional[str] = None

class Ld(BaseModel):
    lead: str
    variant: str
    r: float
    ld_block: str

class Gene(BaseModel):
    symbol: str
    chr: int 
    min_bp: int
    max_bp: int

class GeneMetadata(BaseModel):
    symbol: str
    chr: int 
    min_bp: int
    max_bp: int

class ExtendedColoc(Coloc):
    association: Optional[Association] = None

class Study(BaseModel):
    data_type: str
    data_format: str
    study_name: str
    trait: str
    ancestry: Optional[str] = None
    sample_size: Optional[int] = None
    category: Optional[str] = None
    study_location: str
    extracted_location: str
    reference_build: str
    p_value_threshold: float
    gene: Optional[str] = None
    probe: Optional[str] = None
    tissue: Optional[str] = None
    source: str
    variant_type: Optional[str] = None


class StudyExtaction(BaseModel):
    study: str
    unique_study_id: str
    file: str
    chr: int 
    bp: int
    min_p: float
    cis_trans: Optional[str] = None
    ld_block: str
    known_gene: Optional[str] = None
    candidate_snp: str
    trait: str
    data_type: str
    tissue: Optional[str] = None

class SearchTerm(BaseModel):
    type: str
    name: Optional[str] = None
    type_id: Optional[str] = None

class RareComparisons(BaseModel):
    id: Optional[int] = None
    study_name: str
    trait: str
    ancestry: Optional[str] = None
    sample_size: Optional[int] = None
    category: Optional[str] = None
    study_location: str
    extracted_location: str
    reference_build: str
    p_value_threshold: float
    variant_type: Optional[str] = None
    gene: Optional[str] = None

class Variant(BaseModel):
    SNP: Optional[str] = None
    CHR: Optional[int] = None
    BP: Optional[int] = None
    EA: Optional[str] = None
    OA: Optional[str] = None
    Gene: Optional[str] = None
    Feature_type: Optional[str] = None
    Consequence: Optional[str] = None
    cDNA_position: Optional[str] = None
    CDS_position: Optional[str] = None
    Protein_position: Optional[str] = None
    Amino_acids: Optional[str] = None
    Codons: Optional[str] = None
    RSID: Optional[str] = None
    impact: Optional[str] = None
    symbol: Optional[str] = None
    biotype: Optional[str] = None
    strand: Optional[int] = None
    canonical: Optional[str] = None
    ALL_AF: Optional[float] = None
    EUR_AF: Optional[float] = None
    EAS_AF: Optional[float] = None
    AMR_AF: Optional[float] = None
    AFR_AF: Optional[float] = None
    SAS_AF: Optional[float] = None
    ld_block: Optional[str] = None


class GeneResponse(BaseModel):
    gene: Gene
    colocs: List[Coloc]
    variants: List[Variant]
    study_extractions: List[StudyExtaction]

class Region(BaseModel):
    chr: int 
    start: int
    end: int
    name: str

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

def convert_duckdb_to_pydantic_model(model: BaseModel, results: Union[List[tuple], tuple]) -> Union[List[BaseModel], BaseModel]:
    """
    Convert DuckDB query results to a Pydantic model instance or a list of Pydantic model instances.

    :param results: List of tuples returned from DuckDB query or a single tuple.
    :param model: Pydantic model class to convert the results into.
    :return: List of Pydantic model instances or a single Pydantic model instance.
    """
    # If results is a list of tuples, convert each tuple to a model instance
    if isinstance(results, list):
        if len(results) == 0: return []
        return [model(**{field: row[idx] for idx, field in enumerate(model.model_fields.keys())}) for row in results]
    # If results is a single tuple, convert it to a model instance
    elif isinstance(results, tuple):
        return model(**{field: results[idx] for idx, field in enumerate(model.model_fields.keys())})
    else:
        raise ValueError("Results must be a list of tuples or a single tuple.")

