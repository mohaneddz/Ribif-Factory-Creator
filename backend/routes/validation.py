"""
PDF Validation API Route
Validates PDF documents using LLM to check if they contain sufficient 
technical/industrial project information for RIBIF processing.
"""

import os
import json
from pathlib import Path

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from config import UPLOAD_DIR
from vertex_utils import generate_message
from utils.logger import get_logger

logger = get_logger(__name__)

bp_validation = Blueprint("validation", __name__)

# Minimum required confidence score (0-1)
MIN_CONFIDENCE_THRESHOLD = 0.6

# Validation prompt for LLM
VALIDATION_SYSTEM_PROMPT = """You are a document validation expert for industrial project specifications.
Your task is to analyze PDF documents and determine if they contain sufficient technical information 
for an industrial factory/manufacturing project planning system called RIBIF.

A valid document should contain information about AT LEAST SOME of these categories:
- Project overview (company name, project type, objectives)
- Raw materials and inputs
- Products to be manufactured
- Industrial machines and equipment
- Production processes
- Technical specifications
- Financial or business information

Analyze the document and provide a validation result."""

VALIDATION_PROMPT = """Analyze this PDF document and determine if it contains sufficient technical information 
for an industrial/manufacturing project planning system.

Provide your response in the following JSON format only, with no additional text:
{
    "valid": true/false,
    "confidence": 0.0-1.0,
    "categories_found": ["list of categories detected"],
    "summary": "Brief summary of what the document is about",
    "reason": "Explanation of why the document is valid or invalid"
}

Categories to check for:
- project_info: Company name, project type, strategic objectives
- raw_materials: Input materials, quantities, specifications
- products: Products to be manufactured, production volumes
- machines: Industrial equipment, machinery specifications
- processes: Manufacturing processes, production steps
- technical_specs: Technical requirements, standards, certifications
- financial: Business model, costs, investments

A document is VALID if it contains technical content related to industrial/manufacturing projects.
A document is INVALID if it:
- Is blank or contains very little text
- Is about unrelated topics (personal documents, general articles, etc.)
- Does not contain any industrial/manufacturing project information"""


def extract_text_from_pdf(filepath: str) -> str:
    """Extract text content from PDF file using pypdf."""
    try:
        from pypdf import PdfReader
        
        reader = PdfReader(filepath)
        text_parts = []
        
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        
        return "\n\n".join(text_parts)
    except Exception as e:
        logger.error(f"PDF text extraction error: {e}")
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")


def validate_pdf_with_llm(pdf_bytes: bytes) -> dict:
    """
    Validate PDF content using Gemini LLM.
    
    Args:
        pdf_bytes: Raw bytes of the PDF file
        
    Returns:
        Dictionary with validation result
    """
    import base64
    
    try:
        # Encode PDF for Gemini
        pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
        
        # Call Gemini with the PDF document
        response = generate_message(
            prompt=VALIDATION_PROMPT,
            system_instruction=VALIDATION_SYSTEM_PROMPT,
            documents=[pdf_base64],
            temperature=0.2,  # Lower temperature for more consistent validation
        )
        
        # Parse the JSON response
        response_text = response.strip()
        
        # Try to extract JSON from the response
        if response_text.startswith("```"):
            # Remove markdown code blocks if present
            lines = response_text.split("\n")
            json_lines = []
            in_json = False
            for line in lines:
                if line.startswith("```json"):
                    in_json = True
                    continue
                elif line.startswith("```"):
                    in_json = False
                    continue
                if in_json or (not line.startswith("```")):
                    json_lines.append(line)
            response_text = "\n".join(json_lines).strip()
        
        # Find JSON object in response
        start_idx = response_text.find("{")
        end_idx = response_text.rfind("}") + 1
        if start_idx != -1 and end_idx > start_idx:
            response_text = response_text[start_idx:end_idx]
        
        validation_result = json.loads(response_text)
        
        # Ensure required fields
        return {
            "valid": validation_result.get("valid", False),
            "confidence": validation_result.get("confidence", 0.0),
            "categories_found": validation_result.get("categories_found", []),
            "summary": validation_result.get("summary", ""),
            "reason": validation_result.get("reason", "Validation completed"),
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.error(f"Response was: {response_text[:500] if 'response_text' in dir() else 'N/A'}")
        return {
            "valid": False,
            "confidence": 0.0,
            "categories_found": [],
            "summary": "",
            "reason": "Failed to parse validation response",
            "error": str(e),
        }
    except Exception as e:
        logger.error(f"LLM validation error: {e}")
        return {
            "valid": False,
            "confidence": 0.0,
            "categories_found": [],
            "summary": "",
            "reason": f"Validation failed: {str(e)}",
            "error": str(e),
        }


@bp_validation.route("/api/validate-pdf", methods=["POST"])
def validate_pdf():
    """
    Validate a PDF document for RIBIF processing.
    
    Expects:
        - file: PDF file in multipart form data
        
    Returns:
        JSON response with validation result:
        {
            "valid": boolean,
            "confidence": float (0-1),
            "categories_found": list of detected content categories,
            "summary": brief document summary,
            "reason": explanation of validation result,
            "message": user-friendly message
        }
    """
    # Check if file is provided
    if "file" not in request.files:
        return jsonify({
            "valid": False,
            "error": "No file uploaded",
            "message": "Veuillez télécharger un fichier PDF",
        }), 400
    
    file = request.files["file"]
    
    if file.filename == "":
        return jsonify({
            "valid": False,
            "error": "Empty filename",
            "message": "Le nom du fichier est vide",
        }), 400
    
    # Check file type
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({
            "valid": False,
            "error": "Invalid file type",
            "message": "Seuls les fichiers PDF sont acceptés",
        }), 400
    
    try:
        # Read file bytes
        pdf_bytes = file.read()
        
        # Check file size (max 50MB)
        max_size = 50 * 1024 * 1024  # 50MB
        if len(pdf_bytes) > max_size:
            return jsonify({
                "valid": False,
                "error": "File too large",
                "message": "Le fichier dépasse la taille maximale de 50MB",
            }), 400
        
        # Validate with LLM
        logger.info(f"Validating PDF: {file.filename} ({len(pdf_bytes)} bytes)")
        validation_result = validate_pdf_with_llm(pdf_bytes)
        
        # Check confidence threshold
        confidence = validation_result.get("confidence", 0.0)
        is_valid = validation_result.get("valid", False) and confidence >= MIN_CONFIDENCE_THRESHOLD
        
        # Build response
        response = {
            "valid": is_valid,
            "confidence": confidence,
            "categories_found": validation_result.get("categories_found", []),
            "summary": validation_result.get("summary", ""),
            "reason": validation_result.get("reason", ""),
        }
        
        # Add user-friendly message
        if is_valid:
            response["message"] = "Document validé avec succès. Il contient les informations techniques nécessaires."
        else:
            if confidence < MIN_CONFIDENCE_THRESHOLD and validation_result.get("valid"):
                response["message"] = "Le document semble contenir des informations techniques mais avec un niveau de confiance insuffisant."
            elif not validation_result.get("valid"):
                response["message"] = validation_result.get("reason", "Le document ne contient pas suffisamment d'informations techniques industrielles.")
            else:
                response["message"] = "Le document ne peut pas être utilisé pour ce système."
        
        if "error" in validation_result:
            response["error"] = validation_result["error"]
        
        status_code = 200 if is_valid else 422  # 422 Unprocessable Entity for invalid documents
        return jsonify(response), status_code
        
    except ValueError as e:
        logger.error(f"PDF validation error: {e}")
        return jsonify({
            "valid": False,
            "error": str(e),
            "message": "Erreur lors de l'analyse du document PDF",
        }), 400
        
    except Exception as e:
        logger.error(f"Unexpected validation error: {e}")
        return jsonify({
            "valid": False,
            "error": str(e),
            "message": "Une erreur inattendue s'est produite lors de la validation",
        }), 500


@bp_validation.route("/api/extract-text", methods=["POST"])
def extract_text():
    """
    Extract text from a PDF document.
    
    Expects:
        - file: PDF file in multipart form data
        
    Returns:
        JSON response with extracted text:
        {
            "text": extracted text content,
            "page_count": number of pages,
            "character_count": total characters
        }
    """
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files["file"]
    
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400
    
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are accepted"}), 400
    
    try:
        # Save temporarily
        filename = secure_filename(file.filename)
        filepath = UPLOAD_DIR / f"temp_{filename}"
        file.save(filepath)
        
        try:
            # Extract text
            text = extract_text_from_pdf(str(filepath))
            
            # Count pages
            from pypdf import PdfReader
            reader = PdfReader(str(filepath))
            page_count = len(reader.pages)
            
            return jsonify({
                "text": text,
                "page_count": page_count,
                "character_count": len(text),
            })
        finally:
            # Clean up temp file
            if filepath.exists():
                filepath.unlink()
                
    except Exception as e:
        logger.error(f"Text extraction error: {e}")
        return jsonify({"error": str(e)}), 500
