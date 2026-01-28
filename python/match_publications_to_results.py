import json
import re
from difflib import SequenceMatcher
from pathlib import Path

# Parse the Revised Publications.txt
publications_file = Path(__file__).parent.parent / "Documents" / "Revised Publications.txt"
pubmed_results = Path(__file__).parent / "pubmed_residents_results.json"

def parse_publications_file(filepath):
    """Parse Revised Publications.txt and return dict of resident -> actions -> papers"""
    residents = {}
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # Format: Name - Title - Journal - ACTION
            parts = line.split(' - ')
            if len(parts) < 4:
                continue
            
            name = parts[0].strip()
            action = parts[-1].strip().upper()  # Last part is action
            journal = parts[-2].strip()  # Second-to-last is journal
            title = ' - '.join(parts[1:-2]).strip()  # Everything between name and journal
            
            if name not in residents:
                residents[name] = {'ADD': [], 'DELETE': [], 'KEEP': []}
            
            if action in residents[name]:
                residents[name][action].append({
                    'title': title,
                    'journal': journal
                })
    
    return residents

def load_pubmed_results(filepath):
    """Load PubMed results JSON"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return []

def fuzzy_match(title1, title2, threshold=0.85):
    """Fuzzy match titles; return True if similarity > threshold"""
    s = SequenceMatcher(None, title1.lower(), title2.lower())
    return s.ratio() > threshold

def normalize_journal(journal):
    """Normalize journal name for comparison"""
    return journal.lower().strip()

def find_paper(paper, resident_publications):
    """Find matching paper in resident's PubMed results"""
    if not resident_publications:
        return None
    
    target_title = paper['title'].lower()
    target_journal = normalize_journal(paper['journal'])
    
    for pub in resident_publications:
        pub_title = pub.get('title', '').lower()
        pub_journal = normalize_journal(pub.get('journal', ''))
        
        # Try exact journal match first, then fuzzy title match
        if target_journal in pub_journal or pub_journal in target_journal:
            if fuzzy_match(target_title, pub_title, threshold=0.8):
                return pub
    
    # Fallback: just try fuzzy title match if journal didn't match
    for pub in resident_publications:
        pub_title = pub.get('title', '').lower()
        if fuzzy_match(target_title, pub_title, threshold=0.85):
            return pub
    
    return None

def main():
    # Parse publication actions
    print("Parsing publications file...")
    residents_actions = parse_publications_file(publications_file)
    print(f"Found actions for {len(residents_actions)} residents\n")
    
    # Load PubMed results
    print("Loading PubMed results...")
    pubmed_data = load_pubmed_results(pubmed_results)
    pubmed_index = {item.get('resident_name'): item.get('publications', []) for item in pubmed_data}
    print(f"Loaded PubMed data for {len(pubmed_index)} residents\n")
    
    # Match and report
    output = {
        'summary': {
            'total_residents': len(residents_actions),
            'residents_processed': 0,
            'total_papers': 0,
            'papers_found': 0,
            'papers_missing': 0
        },
        'residents': {}
    }
    
    for resident_name, actions in residents_actions.items():
        pubmed_pubs = pubmed_index.get(resident_name, [])
        
        resident_report = {
            'actions': {}
        }
        
        for action, papers in actions.items():
            if not papers:
                continue
            
            action_report = {
                'total': len(papers),
                'found': 0,
                'missing': 0,
                'papers': []
            }
            
            for paper in papers:
                match = find_paper(paper, pubmed_pubs)
                status = 'FOUND' if match else 'MISSING'
                
                paper_record = {
                    'title': paper['title'],
                    'journal': paper['journal'],
                    'status': status
                }
                
                if match:
                    action_report['found'] += 1
                    output['summary']['papers_found'] += 1
                else:
                    action_report['missing'] += 1
                    output['summary']['papers_missing'] += 1
                
                action_report['papers'].append(paper_record)
            
            resident_report['actions'][action] = action_report
            output['summary']['total_papers'] += len(papers)
        
        if resident_report['actions']:
            output['residents'][resident_name] = resident_report
            output['summary']['residents_processed'] += 1
    
    # Write output
    output_path = Path(__file__).parent / "publication_matching_report.json"
    output_path.write_text(json.dumps(output, indent=2), encoding='utf-8')
    
    print("=" * 80)
    print("PUBLICATION MATCHING REPORT")
    print("=" * 80)
    print(f"\nTotal residents: {output['summary']['total_residents']}")
    print(f"Residents processed: {output['summary']['residents_processed']}")
    print(f"Total papers to find: {output['summary']['total_papers']}")
    print(f"Papers found: {output['summary']['papers_found']}")
    print(f"Papers missing: {output['summary']['papers_missing']}")
    if output['summary']['total_papers'] > 0:
        pct = (output['summary']['papers_found'] / output['summary']['total_papers']) * 100
        print(f"Match rate: {pct:.1f}%")
    
    print(f"\nDetailed report saved to: {output_path}\n")
    
    # Print summary by action
    total_by_action = {'ADD': 0, 'DELETE': 0, 'KEEP': 0}
    found_by_action = {'ADD': 0, 'DELETE': 0, 'KEEP': 0}
    
    for resident_name, report in output['residents'].items():
        for action, action_data in report['actions'].items():
            total_by_action[action] += action_data['total']
            found_by_action[action] += action_data['found']
    
    print("Breakdown by action:")
    for action in ['ADD', 'DELETE', 'KEEP']:
        if total_by_action[action] > 0:
            pct = (found_by_action[action] / total_by_action[action]) * 100
            print(f"  {action}: {found_by_action[action]}/{total_by_action[action]} found ({pct:.1f}%)")

if __name__ == '__main__':
    main()
