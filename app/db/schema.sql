CREATE TABLE IF NOT EXISTS "ancestry" (
	"id" bigint NOT NULL,
	"ancestry" varchar(255) NOT NULL,
	PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "ontology" (
	"name" varchar(255) NOT NULL,
	"uri" varchar(255) NOT NULL,
	PRIMARY KEY ("name")
);

CREATE TABLE IF NOT EXISTS "traits" (
	"trait_name" varchar(255) NOT NULL,
	"study" bigint NOT NULL,
	"ontology" varchar(255) NOT NULL,
	"sample_size" bigint NOT NULL,
	"ncase" bigint NOT NULL,
	"ncontrol" bigint NOT NULL,
	"units" varchar(255) NOT NULL,
	"ancestry" bigint NOT NULL,
	"type" varchar(255) NOT NULL,
	"id" bigint NOT NULL,
	PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "variants" (
	"id" bigint NOT NULL,
	"chr" bigint NOT NULL,
	"pos" bigint NOT NULL,
	"a1" varchar(255) NOT NULL,
	"a2" varchar(255) NOT NULL,
	"causal" boolean NOT NULL,
	"sas_freq" double precision NOT NULL,
	"eas_freq" double precision NOT NULL,
	"eur_freq" double precision NOT NULL,
	"afr_freq" double precision NOT NULL,
	"his_freq" double precision NOT NULL,
	"sas_ldscore" double precision NOT NULL,
	"eas_ldscore" double precision NOT NULL,
	"eur_ldscore" double precision NOT NULL,
	"afr_ldscore" double precision NOT NULL,
	"his_ldscore" double precision NOT NULL,
	PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "ld" (
	"id" bigint NOT NULL,
	"id1" bigint NOT NULL,
	"id2" bigint NOT NULL,
	"ancestry" bigint NOT NULL,
	"r_eur" double precision NOT NULL,
	"r_sas" double precision NOT NULL,
	"r_eas" double precision NOT NULL,
	"r_afr" double precision NOT NULL,
	"r_his" double precision NOT NULL,
	PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "finemap" (
	"id" bigint NOT NULL,
	"leadsnp" bigint NOT NULL,
	"trait" bigint NOT NULL,
	PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "assocs" (
	"id" bigint NOT NULL,
	"variant" bigint NOT NULL,
	"trait" bigint NOT NULL,
	"beta" double precision NOT NULL,
	"se" double precision NOT NULL,
	"pval" double precision NOT NULL,
	PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "coloc" (
	"id" bigint NOT NULL,
	"trait" bigint NOT NULL,
	"candidate_snp" bigint NOT NULL,
	"posterior_prob" double precision NOT NULL,
	"posterior_explained_by_snp" double precision NOT NULL,
	PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "studies" (
	"id" bigint NOT NULL,
	"pubmed" bigint,
	"doi" varchar,
	"url" varchar,
	"title" varchar,
	PRIMARY KEY ("id")
);


ALTER TABLE "traits" ADD CONSTRAINT "traits_fk1" FOREIGN KEY ("study") REFERENCES "studies"("id");
ALTER TABLE "traits" ADD CONSTRAINT "traits_fk2" FOREIGN KEY ("ontology") REFERENCES "ontology"("name");
ALTER TABLE "traits" ADD CONSTRAINT "traits_fk7" FOREIGN KEY ("ancestry") REFERENCES "ancestry"("id");
ALTER TABLE "ld" ADD CONSTRAINT "ld_fk1" FOREIGN KEY ("id1") REFERENCES "variants"("id");
ALTER TABLE "ld" ADD CONSTRAINT "ld_fk2" FOREIGN KEY ("id2") REFERENCES "variants"("id");
ALTER TABLE "ld" ADD CONSTRAINT "ld_fk3" FOREIGN KEY ("ancestry") REFERENCES "ancestry"("id");
ALTER TABLE "finemap" ADD CONSTRAINT "finemap_fk1" FOREIGN KEY ("leadsnp") REFERENCES "variants"("id");
ALTER TABLE "finemap" ADD CONSTRAINT "finemap_fk2" FOREIGN KEY ("trait") REFERENCES "traits"("id");
ALTER TABLE "assocs" ADD CONSTRAINT "assocs_fk1" FOREIGN KEY ("variant") REFERENCES "variants"("id");
ALTER TABLE "assocs" ADD CONSTRAINT "assocs_fk2" FOREIGN KEY ("trait") REFERENCES "finemap"("id");
ALTER TABLE "coloc" ADD CONSTRAINT "coloc_fk1" FOREIGN KEY ("trait") REFERENCES "finemap"("id");
ALTER TABLE "coloc" ADD CONSTRAINT "coloc_fk2" FOREIGN KEY ("candidate_snp") REFERENCES "variants"("id");
