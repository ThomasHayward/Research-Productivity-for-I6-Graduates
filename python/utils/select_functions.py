from typing import Dict, List, Optional

from .constants import (AUTHOR, AUTHOR_PUBLICATION, FELLOWSHIP, GRANT, JOURNAL,
                        MEDICAL_SCHOOL, POST_RESIDENCY_CAREER, PUBLICATION,
                        RESIDENCY, RESIDENT, TABLES)


def format_sql_value(value: any) -> str:
    """Helper function to format values for SQL queries"""
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return str(value)
    # For strings, escape single quotes and wrap in quotes
    return f"'{str(value).replace('\'', '\'\'')}'"

def select_from_table(cursor, table_name: str, fields: Optional[List[str]] = None):
    """Same documentation as before, but now executes the query directly"""
    query = f"SELECT * FROM {table_name}" if not fields else f"SELECT {', '.join(fields)} FROM {table_name}"
    cursor.execute(query)
    return cursor.fetchall()

def select_with_condition(cursor, table_name: str, 
                         fields: Optional[List[str]] = None, 
                         conditions: Optional[Dict[str, any]] = None):
    """Same documentation as before, but now executes the query directly"""
    base_query = f"SELECT * FROM {table_name}" if not fields else f"SELECT {', '.join(fields)} FROM {table_name}"
    
    if conditions:
        where_conditions = " AND ".join([f"{field} = {format_sql_value(value)}" 
                                       for field, value in conditions.items()])
        query = f"{base_query} WHERE {where_conditions}"
    else:
        query = base_query
        
    cursor.execute(query)
    return cursor.fetchall()

def insert_into_table(cursor, table_name: str, field_values: Dict[str, any]) -> bool:
    """Same documentation as before, but now executes the query directly"""
    fields = list(field_values.keys())
    values = list(field_values.values())
    
    fields_str = ", ".join(fields)
    values_str = ", ".join([format_sql_value(v) for v in values])
    
    query = f"INSERT INTO {table_name} ({fields_str}) VALUES ({values_str})"
    cursor.execute(query)
    cursor.commit()
    return True

def insert_multiple(cursor, table_name: str, fields: List[str], value_sets: List[List[any]]) -> bool:
    """Same documentation as before, but now executes the query directly"""
    fields_str = ", ".join(fields)
    
    value_strings = []
    for value_set in value_sets:
        values_str = ", ".join([format_sql_value(v) for v in value_set])
        value_strings.append(f"({values_str})")
    
    all_values_str = ", ".join(value_strings)
    query = f"INSERT INTO {table_name} ({fields_str}) VALUES {all_values_str}"
    
    cursor.execute(query)
    cursor.commit()
    return True

def exists_in_table(cursor, table_name: str, conditions: Dict[str, any]) -> bool:
    """Same documentation as before, but now executes the query directly"""
    where_conditions = " AND ".join([f"{field} = {format_sql_value(value)}" 
                                   for field, value in conditions.items()])
    query = f"SELECT EXISTS(SELECT 1 FROM {table_name} WHERE {where_conditions})"
    
    cursor.execute(query)
    return cursor.fetchone()[0] == 1

def count_in_table(cursor, table_name: str, conditions: Optional[Dict[str, any]] = None) -> int:
    """Same documentation as before, but now executes the query directly"""
    query = f"SELECT COUNT(*) FROM {table_name}"
    
    if conditions:
        where_conditions = " AND ".join([f"{field} = {format_sql_value(value)}" 
                                       for field, value in conditions.items()])
        query = f"{query} WHERE {where_conditions}"
    
    cursor.execute(query)
    return cursor.fetchone()[0]

def insert_if_not_exists(cursor, table: str, check_fields: dict, insert_fields: dict = None) -> bool:
    """Same documentation as before, but now uses the new execution methods"""
    if insert_fields is None:
        insert_fields = check_fields
    
    # Use exists_in_table to check existence
    if not exists_in_table(cursor, table, check_fields):
        return insert_into_table(cursor, table, insert_fields)
    return False

def update_table(cursor, table_name: str, update_fields: Dict[str, any], conditions: Dict[str, any]) -> bool:
    """Update fields in a table for records matching conditions."""
    set_clause = ", ".join([f"{field} = {format_sql_value(value)}" for field, value in update_fields.items()])
    where_clause = " AND ".join([f"{field} = {format_sql_value(value)}" for field, value in conditions.items()])
    query = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"
    cursor.execute(query)
    cursor.commit()
    return True
