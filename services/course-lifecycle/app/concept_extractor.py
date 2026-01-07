import hashlib
import re
from typing import List, Dict, Tuple, Set
from .graph_schema import ConceptNode, RelationEdge

def generate_concept_id(label: str) -> str:
    """Stable ID based on label: c_ + sha1[:12]"""
    hash_digest = hashlib.sha1(label.lower().strip().encode()).hexdigest()
    return f"c_{hash_digest[:12]}"

class ConceptExtractor:
    """
    Simple heuristic-based concept extractor.
    """
    
    def extract(self, slides: List[Dict]) -> Tuple[List[ConceptNode], List[RelationEdge], Dict[str, List[str]]]:
        """
        Extracts concepts and relations from slides.
        Returns:
            - concepts: List of extracted ConceptNodes
            - relations: List of extracted RelationEdges
            - slide_concept_map: Mapping of slide_id (or index) to list of concept IDs
        """
        concepts_map: Dict[str, ConceptNode] = {}
        relations: List[RelationEdge] = []
        slide_map: Dict[str, List[str]] = {} # slide_index -> [concept_ids]
        
        # 1. Extract Candidates (Capitalized phrases, specialized terms)
        for i, slide in enumerate(slides):
            text = f"{slide.get('title', '')} {' '.join(slide.get('bullets', []))} {slide.get('speaker_notes', '')}"
            
            # Simple identifying of 'Key Terms' (Capitalized Words inside sentence)
            candidates = self._find_candidates(text)
            
            slide_concepts = []
            
            for term in candidates:
                term_key = term.lower()
                cid = generate_concept_id(term)
                
                if cid not in concepts_map:
                    concepts_map[cid] = ConceptNode(
                        id=cid,
                        label=term,
                        description=f"Extracted from slide {i+1}",
                        tags=["extracted"]
                    )
                
                if cid not in slide_concepts:
                    slide_concepts.append(cid)
            
            # Associate distinct concepts found in same slide as "RELATED"
            # Simple co-occurrence
            if len(slide_concepts) > 1:
                # Link first 2-3 for simplicity to avoid clique explosion
                for idx_a in range(len(slide_concepts)):
                    for idx_b in range(idx_a + 1, min(len(slide_concepts), idx_a + 3)):
                        src = slide_concepts[idx_a]
                        tgt = slide_concepts[idx_b]
                        # Add undirected relation (represented as two directed or one?)
                        # Schema has source/target.
                        relations.append(RelationEdge(
                            source_id=src,
                            target_id=tgt,
                            relation_type="CO_OCCURRENCE",
                            confidence=0.5,
                            evidence=f"Slide {i+1}"
                        ))

            slide_map[str(i+1)] = slide_concepts # Key by slide_no (1-based)
            
        return list(concepts_map.values()), relations, slide_map

    def _find_candidates(self, text: str) -> Set[str]:
        # Regex for Capitalized Phrases (e.g. "Machine Learning", "Data Science")
        # Exclude start of sentence? Hard to detect without NLP punctuation splitting.
        # Just grab NNP-like patterns.
        # Pattern: Word starting with Upper, followed optionally by spaces and more Upper words.
        pattern = r'\b[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*\b'
        matches = re.findall(pattern, text)
        
        # Filter common stopwords or generic terms
        stopwords = {"The", "A", "An", "In", "On", "For", "To", "Of", "And", "With", "Slide", "Introduction", "Summary"}
        candidates = set()
        for m in matches:
            if len(m) < 3: continue 
            if m in stopwords: continue
            if m.lower() in {s.lower() for s in stopwords}: continue
            
            candidates.add(m)
            
        return candidates
