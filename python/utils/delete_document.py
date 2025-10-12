from typing import Dict, List, Optional

from .constants import (AUTHOR, AUTHOR_PUBLICATION, FELLOWSHIP, GRANT, JOURNAL,
                        MEDICAL_SCHOOL, POST_RESIDENCY_CAREER, PUBLICATION,
                        RESIDENCY, RESIDENT, TABLES)
from .select_functions import format_sql_value


def delete_from_table(cursor, table_name: str, conditions: Dict[str, any]) -> bool:
    """
    Delete records from a table that match the given conditions
    
    Args:
        cursor: Database cursor
        table_name: Name of the table to delete from
        conditions: Dictionary of field-value pairs to match for deletion
        
    Returns:
        bool: True if deletion was successful
    """
    try:
        where_conditions = " AND ".join([f"{field} = {format_sql_value(value)}" 
                                       for field, value in conditions.items()])
        query = f"DELETE FROM {table_name} WHERE {where_conditions}"
        cursor.execute(query)
        cursor.commit()
        return True
    except Exception as e:
        print(f"Error deleting from {table_name}: {e}")
        return False

def delete_publication(cursor, author_id: int, title: str, journal: str) -> bool:
    """
    Delete a publication and its associated author relationship
    
    Args:
        cursor: Database cursor
        author_id: ID of the author
        title: Title of the publication
        journal: Name of the journal
        
    Returns:
        bool: True if deletion was successful
    """
    try:
        # First find the publication ID with case-insensitive matching
        cursor.execute(f"""
            SELECT p.id 
            FROM {TABLES['PUBLICATION']} p
            JOIN {TABLES['JOURNAL']} j ON p.journal_id = j.id
            WHERE LOWER(p.topic) = LOWER(?) AND LOWER(j.name) = LOWER(?)
        """, (title, journal))
        
        result = cursor.fetchone()
        if not result:
            print(f"Publication not found: {title}")
            return False
            
        pub_id = result[0]
        
        # Delete from author_publication
        cursor.execute(f"""
            DELETE FROM {TABLES['AUTHOR_PUBLICATION']} 
            WHERE author_id = ? AND publication_id = ?
        """, (author_id, pub_id))
        
        # Check if publication has other authors
        cursor.execute(f"""
            SELECT COUNT(*) FROM {TABLES['AUTHOR_PUBLICATION']}
            WHERE publication_id = ?
        """, (pub_id,))
        
        if cursor.fetchone()[0] == 0:
            # No other authors, safe to delete publication
            cursor.execute(f"""
                DELETE FROM {TABLES['PUBLICATION']} 
                WHERE id = ?
            """, (pub_id,))
        
        cursor.commit()
        return True
    except Exception as e:
        print(f"Error deleting publication {title}: {e}")
        return False

def delete_resident_publications(cursor, resident_id: int, keep_titles: List[str] = None) -> bool:
    """
    Delete all publications for a resident except those in keep_titles
    
    Args:
        cursor: Database cursor
        resident_id: ID of the resident
        keep_titles: List of publication titles to keep (optional)
        
    Returns:
        bool: True if deletion was successful
    """
    try:
        if keep_titles:
            print(f"DEBUG: Resident ID: {resident_id}")
            print(f"DEBUG: Number of titles to keep: {len(keep_titles)}")
            print(f"DEBUG: Keep titles: {keep_titles}")

            # First, get the publication IDs we want to keep
            values_list = ' UNION ALL '.join([f'SELECT ? AS title' for _ in keep_titles])
            keep_query = f"""
                SELECT DISTINCT p.id
                FROM {TABLES['PUBLICATION']} p
                INNER JOIN {TABLES['AUTHOR_PUBLICATION']} ap ON p.id = ap.publication_id
                INNER JOIN {TABLES['AUTHOR']} a ON ap.author_id = a.id
                WHERE a.resident_id = ?
                AND EXISTS (
                    SELECT 1 FROM ({values_list}) AS titles
                    WHERE LOWER(p.topic) = LOWER(titles.title)
                )
            """
            params = [resident_id] + keep_titles
            cursor.execute(keep_query, params)
            keep_pub_ids = [str(row[0]) for row in cursor.fetchall()]
            
            if not keep_pub_ids:
                print("Warning: None of the publications to keep were found!")
                return False
                
            # Delete all author_publications for this resident except those we want to keep
            query = f"""
                DELETE ap
                FROM {TABLES['AUTHOR_PUBLICATION']} ap
                INNER JOIN {TABLES['AUTHOR']} a ON ap.author_id = a.id
                WHERE a.resident_id = ?
                AND ap.publication_id NOT IN ({','.join(keep_pub_ids)})
            """
            cursor.execute(query, (resident_id,))
            print(f"DEBUG: Rows affected by delete: {cursor.rowcount}")

            # Clean up orphaned publications
            cleanup_query = f"""
                DELETE p
                FROM {TABLES['PUBLICATION']} p
                LEFT JOIN {TABLES['AUTHOR_PUBLICATION']} ap ON p.id = ap.publication_id
                WHERE ap.publication_id IS NULL
            """
            cursor.execute(cleanup_query)
        else:
            # Delete all author_publications for this resident
            query = f"""
                DELETE ap
                FROM {TABLES['AUTHOR_PUBLICATION']} ap
                INNER JOIN {TABLES['AUTHOR']} a ON ap.author_id = a.id
                WHERE a.resident_id = ?
            """
            cursor.execute(query, (resident_id,))

            # Clean up orphaned publications
            cleanup_query = f"""
                DELETE p
                FROM {TABLES['PUBLICATION']} p
                LEFT JOIN {TABLES['AUTHOR_PUBLICATION']} ap ON p.id = ap.publication_id
                WHERE ap.publication_id IS NULL
            """
            cursor.execute(cleanup_query)

        cursor.commit()
        return True
    except Exception as e:
        print(f"Error deleting resident publications: {e}")
        return False
