from .constants import (AUTHOR, AUTHOR_PUBLICATION, FELLOWSHIP, JOURNAL,
                        MEDICAL_SCHOOL, POST_RESIDENCY_CAREER, PUBLICATION,
                        RESIDENCY, RESIDENT, TABLES)
from .select_functions import (insert_if_not_exists, select_from_table,
                               select_with_condition)


def find_author_in_authors_list(author, authors):
    """
    Given an author and list of authors, return the index of the author in the list.
    """
    def get_middle_initial(val):
        # Accepts None, '', or full middle name, returns first letter upper or ''
        if not val:
            return ''
        return val[0].upper()

    author_first = (getattr(author, 'first_name', '') or '').strip().lower()
    author_last = (getattr(author, 'last_name', '') or '').strip().lower()
    author_mi = get_middle_initial(getattr(author, 'middle_name', None) or getattr(author, 'middle_initial', None) or '')
    for i, a in enumerate(authors):
        first_match = (a.get("firstname", "") or "").strip().lower() == author_first
        last_match = (a.get("lastname", "") or "").strip().lower() == author_last
        # Try to get middle initial from dict, could be 'middlename', 'middleinitial', or 'middle'
        a_mi = get_middle_initial(a.get("middlename", None) or a.get("middleinitial", None) or a.get("middle", None) or '')
        # If either has no middle initial, ignore it; else, require match
        mi_match = (not author_mi or not a_mi) or (author_mi == a_mi)
        if first_match and last_match and mi_match:
            return i
    return -1


def get_author_ordership_from_list(author, authors):
    """
    Given a list of authors and author, return the order of authorship.
    """
    author_index = find_author_in_authors_list(author, authors)
    
    if author_index == -1:
        return 'unknown'
    elif author_index == 0:
        return '1st'
    elif author_index == 1:
        return '2nd'
    elif author_index == len(authors) - 1:
        return 'last'
    else:
        return 'mid'


def insert_pubmed_article_single_table(cursor, table: str, insert_fields: dict, check_fields: dict = None, conditions=None):
    if check_fields is None:
        check_fields = insert_fields
    if conditions is None:
        conditions = check_fields

    insert_if_not_exists(cursor, table, check_fields, insert_fields)
    results = select_with_condition(cursor, table, conditions=conditions)
    return results[0][0]

def insert_pubmed_full_article(cursor, resident, article, database):
        # print(f"- {article.title}")
        # print(f"  Journal: {article.journal}")
        # print(f"  Date: {article.publication_date}")
        # print(f"  DOI: {article.doi}")
        # print("---")

        author_indx = find_author_in_authors_list(resident, article.authors)
        if author_indx == -1:
            # print(f"Author not found in authors list for article: {article.title}")
            return

        journal_id = insert_pubmed_article_single_table(cursor, TABLES["JOURNAL"], 
            insert_fields={JOURNAL["NAME"]: article.journal})
        # print(f"Journal ID: {journal_id}")
        publication_id = insert_pubmed_article_single_table(cursor, TABLES["PUBLICATION"], 
            insert_fields={
                PUBLICATION["JOURNAL_ID"]: journal_id,
                PUBLICATION["DATE_PUBLISHED"]: article.publication_date,
                PUBLICATION["TOPIC"]: article.title,
                PUBLICATION["DOI"]: article.doi,
            }, 
            conditions={PUBLICATION["TOPIC"]: article.title})
        # print(f"Publication ID: {publication_id}")
        
        # Get author affiliation, use empty string if not found
        author_affiliation = ''
        if author_indx != -1:
            try:
                author_affiliation = article.authors[author_indx].get('affiliation', '') or ''
            except (AttributeError, KeyError, IndexError):
                author_affiliation = ''
            
        author_data = {
            AUTHOR["RESIDENT_ID"]: resident.id,
            AUTHOR["FIRST_ATTENDING_YEAR"]: resident.grad_year,
            AUTHOR["AFFILIATION"]: author_affiliation
        }
        
        author_id = insert_pubmed_article_single_table(cursor, TABLES["AUTHOR"], 
            insert_fields=author_data,
            conditions={AUTHOR["RESIDENT_ID"]: resident.id})
        # print(f"Author ID: {author_id}")
        author_publication_id = insert_pubmed_article_single_table(cursor, TABLES["AUTHOR_PUBLICATION"], 
            insert_fields={
                AUTHOR_PUBLICATION["AUTHOR_ID"]: author_id,
                AUTHOR_PUBLICATION["PUBLICATION_ID"]: publication_id,
                AUTHOR_PUBLICATION["ORDER_OF_AUTHORSHIP"]: get_author_ordership_from_list(resident, article.authors)
            }, 
            conditions={
                AUTHOR_PUBLICATION["AUTHOR_ID"]: author_id, 
                AUTHOR_PUBLICATION["PUBLICATION_ID"]: publication_id
            })
        # print(f"Author Publication ID: {author_publication_id}")
