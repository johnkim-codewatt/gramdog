import json
import re
import os

def parse_markdown():
    with open('wikibooks_english_grammar.md', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by paragraphs
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    return paragraphs

def find_best_match(rule, paragraphs):
    keywords = set(re.findall(r'\b[a-zA-Z]{3,}\b', rule['rule_name'].lower()))
    keywords.update(re.findall(r'\b[a-zA-Z]{3,}\b', rule['core_formula'].lower()))
    
    # Add some specific keywords based on tag_id
    tag_id = rule['tag_id'].lower()
    tag_words = set(re.findall(r'[a-z]+', tag_id))
    keywords.update([w for w in tag_words if len(w) >= 3])
    
    best_score = 0
    best_paragraph = ""
    
    for p in paragraphs:
        # Avoid tables or formatting artifacts
        if p.startswith('|') or p.startswith('---'):
            continue
        
        p_lower = p.lower()
        score = sum(1 for kw in keywords if kw in p_lower)
        
        # Give bonus if actual tag id parts are in the paragraph
        for w in tag_words:
            if len(w) >= 3 and w in p_lower:
                score += 2
                
        # additional penalty for not matching modals if tag_id contains modal concept
        if 'can' in tag_id or 'must' in tag_id or 'should' in tag_id or 'would' in tag_id or 'could' in tag_id or 'might' in tag_id:
            if 'modal' not in p_lower:
                score -= 5
        
        # subjective rules
        if 'wish' in tag_id or 'if_only' in tag_id:
            if 'subjunctive' not in p_lower and 'wish' not in p_lower:
                score -= 5

        if score > best_score:
            best_score = score
            best_paragraph = p

    if best_score > 0 and len(best_paragraph) > 20:
        # truncate to 1000 chars
        if len(best_paragraph) > 997:
            return best_paragraph[:997] + "..."
        return best_paragraph
    else:
        return "No specific description found in Wikibooks English Grammar."

def main():
    with open('grammar_atlas.json', 'r', encoding='utf-8') as f:
        atlas = json.load(f)
        
    paragraphs = parse_markdown()
    
    new_data = []
    for rule in atlas:
        desc = find_best_match(rule, paragraphs)
        new_rule = rule.copy()
        new_rule['original_description'] = desc
        new_data.append(new_rule)
        
    with open('wikibooks_grammar.json', 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)
        
    print(f"Generated wikibooks_grammar.json with {len(new_data)} rules.")

if __name__ == '__main__':
    main()
