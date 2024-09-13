Potential schema

```sql
ancestry {
	id int pk
	ancestry varchar
}

ontology {
	id varchar pk
	name varchar
	uri varchar
}

traits {
	ancestry int > ancestry.id
	id int pk
	trait_name varchar
	study int > studies.id
	ontology varchar > ontology.id
	type varchar
	sample_size int
	ncase int
	ncontrol int
	units varchar
}

studies {
	id int pk
	pubmed int
	doi varchar
	url varchar
	title varchar
}

variants {
	id varchar pk
	chr int
	pos int
	a1 varchar
	a2 varchar
	causal boolean
	sas_freq float
	eas_freq float
	eur_freq float
	afr_freq float
	his_freq float
	sas_ldscore float
	eas_ldscore float
	eur_ldscore float
	afr_ldscore float
	his_ldscore float
}

assocs {
	variant_id varchar pk > finemap.id
	trait_id int > traits.id
	beta float
	se float
	pval float
	n float
	ncase float
	ncontrol float
	info float
	simp_info float
}

ld {
	id1 varchar pk > variants.id
	id2 varchar > variants.id
	ancestry int > ancestry.id
	r_eur float
	r_sas float
	r_eas float
	r_afr float
	r_his float
}

finemap {
	trait int > traits.id
	cs int
	tagsnp varchar > variants.id
	raw bool
	id int pk
}

coloc {
	id int pk
	trait varchar > finemap.id
	posterior_explained_by_snp float
	candidate_snp varchar > variants.id
	posterior_prob float
}



```



Summary statistics stored in gzipped files rather than database

