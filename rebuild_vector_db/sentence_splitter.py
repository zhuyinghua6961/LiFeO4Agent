"""
SentenceSplitter module for splitting cleaned Markdown into sentences.
"""

import re
import json
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple


@dataclass
class SentenceData:
    """Data structure for a sentence."""
    sentence_id: str           # Unique ID: {source}_{section}_{para}_{sent}
    text: str                  # Sentence text
    source: str                # Document identifier
    doi: Optional[str]         # DOI
    section: str               # Section name
    paragraph_index: int       # Paragraph index
    sentence_index: int        # Sentence index
    has_number: bool           # Whether contains numbers
    has_unit: bool             # Whether contains units
    metadata: Dict[str, Any]   # Other metadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'sentence_id': self.sentence_id,
            'text': self.text,
            'source': self.source,
            'doi': self.doi,
            'section': self.section,
            'paragraph_index': self.paragraph_index,
            'sentence_index': self.sentence_index,
            'has_number': self.has_number,
            'has_unit': self.has_unit,
            'metadata': self.metadata
        }


class SentenceSplitter:
    """Splits cleaned Markdown text into sentences."""
    
    def __init__(self, min_sentence_length: int = 10, doi_mapping_file: str = None, filter_references: bool = True):
        """
        Initialize the sentence splitter.
        
        Args:
            min_sentence_length: Minimum length for a valid sentence (default: 10)
            doi_mapping_file: Path to DOI mapping JSON file
            filter_references: Whether to filter out REFERENCES section (default: True)
        """
        self.min_sentence_length = min_sentence_length
        self.doi_mapping_file = doi_mapping_file
        self.filter_references = filter_references
        
        # Load DOI mapping if provided
        self.doi_mapping = {}
        if doi_mapping_file:
            try:
                with open(doi_mapping_file, 'r', encoding='utf-8') as f:
                    self.doi_mapping = json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load DOI mapping file: {e}")
    
    def split(self, text: str, source: str) -> List[SentenceData]:
        """
        Split text into sentences.
        
        Args:
            text: Cleaned Markdown text
            source: Document identifier
            
        Returns:
            List[SentenceData]: List of sentences
        """
        sentences = []
        
        # Extract DOI from source filename
        doi = self._extract_doi(source)
        
        # Split text into paragraphs and track current section
        paragraphs = self._split_into_paragraphs_with_sections(text)
        
        for para_index, paragraph in enumerate(paragraphs):
            section = paragraph['section']
            para_text = paragraph['text']
            
            # Skip empty paragraphs
            if not para_text.strip():
                continue
            
            # Split paragraph into sentences
            para_sentences = self._split_paragraph_into_sentences(para_text)
            
            for sent_index, sentence_text in enumerate(para_sentences):
                # Filter out short sentences
                if len(sentence_text.strip()) < self.min_sentence_length:
                    continue
                
                # Detect numbers and units
                has_number, has_unit = self.detect_numbers_and_units(sentence_text)
                
                # Create sentence ID
                sentence_id = f"{source}_{section}_{para_index}_{sent_index}"
                
                # Create SentenceData object
                sentence_data = SentenceData(
                    sentence_id=sentence_id,
                    text=sentence_text.strip(),
                    source=source,
                    doi=doi,
                    section=section,
                    paragraph_index=para_index,
                    sentence_index=sent_index,
                    has_number=has_number,
                    has_unit=has_unit,
                    metadata={}
                )
                
                sentences.append(sentence_data)
        
        return sentences
    
    def _split_into_paragraphs_with_sections(self, text: str) -> List[Dict[str, Any]]:
        """
        Split text into paragraphs and track section information.
        Filters out REFERENCES section if filter_references is True.
        
        Args:
            text: Input text
            
        Returns:
            List[Dict]: List of paragraph dictionaries with text and section
        """
        paragraphs = []
        current_section = "Unknown"
        in_references = False
        
        # Split by lines
        lines = text.split('\n')
        current_para = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # Check if this line is a section header
            section_match = self._extract_section_from_line(line_stripped)
            if section_match:
                # Check if entering REFERENCES section
                if self.filter_references and section_match.upper() in ['REFERENCES', 'BIBLIOGRAPHY']:
                    # Save current paragraph before stopping
                    if current_para:
                        para_text = ' '.join(current_para)
                        if para_text.strip():
                            paragraphs.append({
                                'text': para_text,
                                'section': current_section
                            })
                        current_para = []
                    # Stop processing - we've reached REFERENCES
                    break
                
                # Save current paragraph before starting new section
                if current_para:
                    para_text = ' '.join(current_para)
                    if para_text.strip():
                        paragraphs.append({
                            'text': para_text,
                            'section': current_section
                        })
                    current_para = []
                
                # Update current section
                current_section = section_match
                continue
            
            # Empty line indicates paragraph break
            if not line_stripped:
                if current_para:
                    para_text = ' '.join(current_para)
                    if para_text.strip():
                        paragraphs.append({
                            'text': para_text,
                            'section': current_section
                        })
                    current_para = []
            else:
                current_para.append(line_stripped)
        
        # Add last paragraph (only if not in references)
        if current_para and not in_references:
            para_text = ' '.join(current_para)
            if para_text.strip():
                paragraphs.append({
                    'text': para_text,
                    'section': current_section
                })
        
        return paragraphs
    
    def _extract_section_from_line(self, line: str) -> Optional[str]:
        """
        Extract section name from a single line if it's a section header.
        
        Args:
            line: Line to check
            
        Returns:
            Optional[str]: Section name if found, None otherwise
        """
        # Match section headers with various formats:
        # ## 1. INTRODUCTION
        # #### 3. RESULTS AND DISCUSSION
        # ## EXPERIMENTAL SECTION
        section_patterns = [
            r'^#{2,4}\s*\d*\.?\s*(INTRODUCTION|ABSTRACT)',
            r'^#{2,4}\s*\d*\.?\s*(METHODS?|METHODOLOGY|EXPERIMENTAL|EXPERIMENTAL\s+SECTION|MATERIALS?\s+AND\s+METHODS?)',
            r'^#{2,4}\s*\d*\.?\s*(RESULTS?|FINDINGS|RESULTS?\s+AND\s+DISCUSSION)',
            r'^#{2,4}\s*\d*\.?\s*(DISCUSSION)',
            r'^#{2,4}\s*\d*\.?\s*(CONCLUSION|CONCLUSIONS?|SUMMARY)',
            r'^#{2,4}\s*\d*\.?\s*(REFERENCES?|BIBLIOGRAPHY)',
            r'^#{2,4}\s*\d*\.?\s*(ACKNOWLEDGMENTS?|ACKNOWLEDGEMENTS?)',
            r'^#{2,4}\s*\d*\.?\s*(ASSOCIATED\s+CONTENT|SUPPORTING\s+INFORMATION)',
            r'^#{2,4}\s*\d*\.?\s*(AUTHOR\s+INFORMATION|AUTHORS?|CORRESPONDING\s+AUTHORS?)',
            r'^#{2,4}\s*\d*\.?\s*(NOTES?)',
            r'^#{2,4}\s*\*?\*?\s*([A-Z][a-zA-Z\s]+)\.\*?\*?',  # Bold section headers like **2.1. Electrode Preparation.**
        ]
        
        for pattern in section_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                section_name = match.group(1).strip()
                # Clean up section name
                section_name = section_name.replace('**', '').strip()
                return section_name
        
        return None
    
    def _split_paragraph_into_sentences(self, paragraph: str) -> List[str]:
        """
        Split a paragraph into sentences using regex.
        
        Splits on: . ! ? 。 ！ ？
        
        Args:
            paragraph: Paragraph text
            
        Returns:
            List[str]: List of sentences
        """
        # Pattern to split on sentence-ending punctuation
        # Matches: . ! ? 。 ！ ？ followed by space or end of string
        # But not: abbreviations like "Dr.", "Fig.", decimal numbers like "3.14"
        
        # First, protect common abbreviations and decimals
        protected = paragraph
        
        # Split on sentence boundaries
        # Use lookahead to keep the punctuation with the sentence
        sentence_pattern = r'(?<=[.!?。！？])\s+(?=[A-Z])|(?<=[.!?。！？])$'
        
        # Alternative: simpler pattern that splits after punctuation
        sentences = re.split(r'([.!?。！？])\s+', protected)
        
        # Reconstruct sentences with their punctuation
        result = []
        i = 0
        while i < len(sentences):
            if i + 1 < len(sentences) and sentences[i + 1] in '.!?。！？':
                # Combine text with its punctuation
                result.append(sentences[i] + sentences[i + 1])
                i += 2
            else:
                if sentences[i].strip():
                    result.append(sentences[i])
                i += 1
        
        # If the simple split didn't work well, use a more robust approach
        if len(result) == 0 or (len(result) == 1 and len(paragraph) > 100):
            # Use a more aggressive splitting pattern
            result = []
            current = []
            
            for char in paragraph:
                current.append(char)
                if char in '.!?。！？':
                    # Check if next char is space or uppercase (sentence boundary)
                    sentence = ''.join(current).strip()
                    if sentence:
                        result.append(sentence)
                    current = []
            
            # Add remaining text
            if current:
                sentence = ''.join(current).strip()
                if sentence:
                    result.append(sentence)
        
        return [s.strip() for s in result if s.strip()]
    
    def _extract_section(self, text: str) -> str:
        """
        Extract section name from text.
        
        Looks for patterns like:
        - ## 1. Introduction
        - ## 2. Methods
        
        Args:
            text: Text to extract section from
            
        Returns:
            str: Section name or "Unknown"
        """
        section_patterns = [
            r'##\s*\d*\.?\s*(Introduction|Abstract)',
            r'##\s*\d*\.?\s*(Methods?|Methodology|Experimental|Materials?\s+and\s+Methods?)',
            r'##\s*\d*\.?\s*(Results?|Findings)',
            r'##\s*\d*\.?\s*(Discussion)',
            r'##\s*\d*\.?\s*(Conclusion|Summary)',
            r'##\s*\d*\.?\s*(References?|Bibliography)',
            r'##\s*\d*\.?\s*(Acknowledgments?|Acknowledgements?)',
            r'##\s*\d*\.?\s*([A-Z][a-zA-Z\s]+)',
        ]
        
        for pattern in section_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return "Unknown"
    
    def _extract_doi(self, source: str) -> Optional[str]:
        """
        Extract DOI from filename using DOI mapping.
        
        Args:
            source: Source filename
            
        Returns:
            Optional[str]: DOI if found, None otherwise
        """
        if not self.doi_mapping:
            return None
        
        # Check if source matches any PDF filename in the mapping
        for doi, pdf_filename in self.doi_mapping.items():
            # Remove extensions for comparison
            pdf_base = pdf_filename.replace('.pdf', '')
            source_base = source.replace('.md', '').replace('_clean', '').replace('_enhanced', '')
            
            # Check if source contains the PDF base name
            if pdf_base in source_base or source_base in pdf_base:
                return doi
        
        return None
    
    def detect_numbers_and_units(self, sentence: str) -> Tuple[bool, bool]:
        """
        Detect whether sentence contains numbers and units.
        
        Args:
            sentence: Sentence text
            
        Returns:
            Tuple[bool, bool]: (has_number, has_unit)
        """
        # Detect numbers (integers, decimals, scientific notation)
        number_patterns = [
            r'\b\d+\.\d+\b',           # Decimal: 3.14
            r'\b\d+\b',                 # Integer: 42
            r'\b\d+\.?\d*[eE][+-]?\d+\b',  # Scientific notation: 1.5e-3, 2E+5
            r'\b\d+\.?\d*\s*[×x]\s*10[⁻⁺]?\d+\b',  # Alternative scientific: 1.5 × 10⁻³
        ]
        
        has_number = False
        for pattern in number_patterns:
            if re.search(pattern, sentence):
                has_number = True
                break
        
        # Detect units (common scientific units)
        unit_patterns = [
            r'\b(V|mV|kV|A|mA|μA|Ah|mAh|Wh|kWh)\b',  # Electrical units
            r'\b(g|mg|μg|kg|mol|mmol|μmol)\b',       # Mass/amount units
            r'\b(m|cm|mm|μm|nm|km)\b',               # Length units
            r'\b(L|mL|μL)\b',                         # Volume units
            r'\b(s|ms|μs|min|h|hr)\b',               # Time units
            r'(°C|°F|K)\b',                           # Temperature units (removed \b at start for °)
            r'\b(Pa|kPa|MPa|GPa|bar|atm)\b',         # Pressure units
            r'\b(Hz|kHz|MHz|GHz)\b',                 # Frequency units
            r'\b(W|mW|kW|MW)\b',                     # Power units
            r'\b(J|kJ|MJ|cal|kcal)\b',               # Energy units
            r'\b(%|ppm|ppb)\b',                       # Concentration units
            r'\b(M|mM|μM)\b',                         # Molarity units
        ]
        
        has_unit = False
        for pattern in unit_patterns:
            if re.search(pattern, sentence):
                has_unit = True
                break
        
        return has_number, has_unit
