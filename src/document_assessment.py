"""Additive PDF-based ESG disclosure screening; does not certify compliance."""
from __future__ import annotations
import re
from io import BytesIO
from typing import Any
from pypdf import PdfReader
from src.config import settings
from src.vector_store import EsgVectorStore

TOPICS = [
("E1","Environmental","GHG emissions",["ghg emissions","scope 1","scope 2","scope 3","carbon emissions","co2e"],"GHG emissions Scope 1 Scope 2 Scope 3 CO2e disclosure"),
("E2","Environmental","Energy use",["energy consumption","energy intensity","renewable energy"],"energy consumption intensity renewable energy"),
("E3","Environmental","Water and wastewater",["water withdrawal","water consumption","wastewater"],"water withdrawal consumption wastewater"),
("E4","Environmental","Waste and circularity",["waste generated","waste recycled","hazardous waste","circular economy"],"waste generation recycling circularity"),
("S1","Social","Workforce health and safety",["occupational health","workplace safety","lost time injury","ltifr"],"employee health safety workplace injuries"),
("S2","Social","Diversity and inclusion",["diversity","gender representation","women in workforce","inclusion"],"workforce diversity equity inclusion"),
("S3","Social","Human rights and labor",["human rights","forced labor","child labor","labor practices"],"human rights labor practices"),
("S4","Social","Community impact",["community investment","community development","social impact"],"community investment social impact"),
("G1","Governance","Board oversight",["board oversight","board independence","sustainability committee","esg committee"],"board oversight board independence ESG committee"),
("G2","Governance","Ethics and anti-corruption",["anti-corruption","anti bribery","code of conduct","whistleblower"],"ethics anti-corruption whistleblower"),
("G3","Governance","Risk management",["risk management","climate risk","enterprise risk"],"enterprise and climate risk management"),
("G4","Governance","Transparency and reporting",["materiality assessment","sustainability reporting","assurance","external assurance"],"ESG materiality reporting external assurance"),
]

def extract_pdf_pages(data: bytes) -> list[dict[str, Any]]:
    reader=PdfReader(BytesIO(data))
    pages=[{"page":i,"text":(p.extract_text() or "").strip()} for i,p in enumerate(reader.pages,1)]
    pages=[p for p in pages if p["text"]]
    if not pages:
        raise ValueError("No selectable text found. This PDF may be scanned; OCR is not included.")
    return pages

def assess_esg_document(filename: str, pdf_bytes: bytes, vector_store: Any|None=None) -> dict[str,Any]:
    pages=extract_pdf_pages(pdf_bytes)
    store=vector_store or EsgVectorStore(settings.chroma_path,settings.chroma_collection,config=settings)
    store.initialize()
    findings=[]
    for ident,pillar,name,terms,query in TOPICS:
        evidence=[]
        for page in pages:
            sentences=[s.strip() for s in re.split(r"(?<=[.!?])\\s+|\\n+",page["text"]) if len(s.strip())>25]
            for sentence in sentences:
                matched=[t for t in terms if t in sentence.lower()]
                if matched:
                    evidence.append({"page":page["page"],"excerpt":sentence[:700],"matched_terms":matched[:5]})
                    if len(evidence)>=3: break
            if len(evidence)>=3: break
        refs=[]
        for r in store.retrieve(query,limit=2):
            meta=r.get("metadata") or {}
            refs.append({"source":meta.get("source","Unknown"),"standard":meta.get("standard","Unknown"),
                         "reference_text":r.get("text",""),"retrieval_score":r.get("score",0.0)})
        status="addressed" if len(evidence)>=2 else ("partial_evidence" if evidence else "not_found")
        findings.append({"id":ident,"pillar":pillar,"name":name,"status":status,"evidence":evidence,
                         "related_references":refs,
                         "assessment_note":("Multiple matching passages found; review cited context." if status=="addressed"
                         else "Potentially relevant text found; verify specificity." if status=="partial_evidence"
                         else "No matching disclosure found in extracted text; this does not establish non-compliance.")})
    counts={s:sum(f["status"]==s for f in findings) for s in ("addressed","partial_evidence","not_found")}
    return {"assessment_type":"document_disclosure_review",
      "document":{"filename":filename,"page_count":len(PdfReader(BytesIO(pdf_bytes)).pages)},
      "status":"completed","summary":{"topic_count":len(findings),"counts":counts},
      "pillars":{p:[f for f in findings if f["pillar"]==p] for p in ("Environmental","Social","Governance")},
      "methodology":"Page-aware PDF text extraction, keyword evidence matching, and related context retrieved from the configured Chroma ESG knowledge base.",
      "limitations":["This is a screening aid, not a legal opinion, audit, certification, or proof of real-world compliance.",
      "Scanned PDFs need OCR; OCR is not included.","Keyword matching can miss relevant text or match without sufficient context.",
      "not_found means no match in this document, not that the company is non-compliant.",
      "The current seeded knowledge base is small and should be expanded and sourced."]}
