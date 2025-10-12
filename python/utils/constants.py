# Table Names Object
TABLES = {
    "RESIDENT": "resident",
    "AUTHOR": "author",
    "PUBLICATION": "publication",
    "AUTHOR_PUBLICATION": "author_publication",
    "JOURNAL": "journal",
    "POST_RESIDENCY_CAREER": "post_residency_career",
    "RESIDENCY": "residency",
    "MEDICAL_SCHOOL": "medical_school",
    "GRANT": "grant",
    "FELLOWSHIP": "fellowship"
}

# Column Objects
RESIDENT = {
    "ID": "id",
    "FIRST_NAME": "first_name",
    "MIDDLE_NAME": "middle_name",
    "LAST_NAME": "last_name",
    "MATCH_YEAR": "match_year",
    "GRAD_YEAR": "grad_year",
    "DURATION": "duration",
    "SEX": "sex",
    "MEDICAL_SCHOOL_RESEARCH_YEARS": "medical_school_research_years",
    "RESIDENCY_RESEARCH_YEARS": "residency_research_years",
    "MEDICAL_SCHOOL_ID": "medical_school_id",
    "RESIDENCY_ID": "residency_id",
    "POST_RESIDENCY_CAREER_ID": "post_residency_career_id",
    "FELLOWSHIP_ID": "fellowship_id"
}

AUTHOR = {
    "ID": "id",
    "RESIDENT_ID": "resident_id",
    "H_INDEX": "h_index",
    "AOA_STATUS": "aoa_status",
    "RANK": "rank",
    "PROGRAM_DIRECTOR": "program_director",
    "FIRST_ATTENDING_YEAR": "first_attending_year",
    "AFFILIATION": "affiliation"
}

PUBLICATION = {
    "ID": "id",
    "JOURNAL_ID": "journal_id",
    "DATE_PUBLISHED": "date_published",
    "TOPIC": "topic",
    "AFFILIATION": "affiliation",
    "DOI": "doi",
    "TYPE": "type"
}

AUTHOR_PUBLICATION = {
    "AUTHOR_ID": "author_id",
    "PUBLICATION_ID": "publication_id",
    "ORDER_OF_AUTHORSHIP": "order_of_authorship"
}

JOURNAL = {
    "ID": "id",
    "NAME": "name",
    "SPECIALTY": "specialty",
    "AVG_IMPACT_FACTOR": "avg_impact_factor",
    "MAX_IMPACT_FACTOR": "max_impact_factor",
    "RANKING": "ranking"
}

POST_RESIDENCY_CAREER = {
    "ID": "id",
    "NAME": "name",
    "TYPE": "type"
}

RESIDENCY = {
    "ID": "id",
    "NAME": "name",
    "RANK": "rank",
    "TYPE": "type"
}

MEDICAL_SCHOOL = {
    "ID": "id",
    "NAME": "name",
    "RANK": "rank"
}

GRANT = {
    "ID": "id",
    "NAME": "name",
    "AMOUNT": "amount",
    "DATE_GRANTED": "date_granted",
    "PUBLICATION_ID": "publication_id"
}

FELLOWSHIP = {
    "ID": "id",
    "NAME": "name",
    "RANK": "rank",
    "INSTITUTION_NAME": "institution_name"
}