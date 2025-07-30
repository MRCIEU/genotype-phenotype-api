from app.models.schemas import Association, Variant
from typing import List

class VariantService:
    def flip_association_data_to_effect_allele(self, associations: List[Association]):
        for association in associations:
            if association.eaf > 0.5:
                association.beta = -association.beta
                association.eaf = 1 - association.eaf
                # association.ea, association.oa = association.oa, association.ea
                
            # TODO: Do we do it via flipped or via eaf?
            # variant = next((v for v in variants if v.id == association.variant_id), None)
            
            # if variant.flipped:
            #     association.beta = -association.beta
            #     association.eaf = 1 - association.eaf
