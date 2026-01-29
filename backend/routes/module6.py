import json
from datetime import date
from flask import Blueprint, jsonify, request

from config import OUTPUT_DIRS, SKIP_MODULE_6, write_json
from supabase_utils import get_supabase, insert_tco_run
from utils.module_6.core import RIBIFModule6TCO, ProductTCO, RawMaterialTCO
from utils.app_helpers import (
    get_request_project_id,
    get_request_user_id,
    insert_tco_details,
    load_template_payload,
    upload_and_register_file,
)

bp_module6 = Blueprint("module6", __name__)


@bp_module6.route("/api/module6/tco-from-sourcing", methods=["POST"])
def calculate_tco_from_sourcing():
    try:
        if SKIP_MODULE_6:
            payload = load_template_payload("module6") or {}
            project_id = get_request_project_id(include_json=True)
            if isinstance(payload, dict) and project_id:
                payload["project_id"] = payload.get("project_id") or project_id
            return jsonify(payload)

        project_id = get_request_project_id(include_json=True)
        module4_id = None

        if not request.is_json:
            return jsonify({"error": "Expected JSON input"}), 400

        data = request.get_json()
        if "data" in data:
            data = data["data"]

        module4_id = data.get("module4_id") or data.get("ribif_metadata", {}).get("module4_id")

        machines_enriched = data.get("machines_enriched", [])
        ribif_metadata = data.get("ribif_metadata", {})

        stage_1 = data.get("stage_1_informations_generales", {})
        stage_2 = data.get("stage_2_matieres_premieres", {})
        stage_3 = data.get("stage_3_produits_fabriques", {})
        stage_4 = data.get("stage_4_machines_equipements", {})
        stage_5 = data.get("stage_5_processus_production", {})
        stage_6 = data.get("stage_6_informations_complementaires", {})

        if not machines_enriched:
            return jsonify({"error": "No enriched machines found in input"}), 400

        tco_calculator = RIBIFModule6TCO()
        all_machine_tcos = []
        all_product_tcos = []

        for idx, machine_item in enumerate(machines_enriched, 1):
            machine_input_raw = machine_item.get("machine_input", {})
            suppliers_raw = machine_item.get("suppliers", [])

            top_supplier = None
            if suppliers_raw:
                sorted_suppliers = sorted(
                    suppliers_raw,
                    key=lambda x: x.get("relevance_score", 0),
                    reverse=True,
                )
                top_supplier = sorted_suppliers[0] if sorted_suppliers else None

            machine_name = machine_input_raw.get("nom_machine", f"Machine_{idx}")
            tco_machine_input = {
                "id": f"machine_{idx}",
                "name": machine_name,
                "category": machine_input_raw.get("type", "Industrial Equipment"),
                "manufacturer": machine_input_raw.get("fabricant_recommande", "Unknown"),
                "base_model": machine_input_raw.get("type", ""),
                "original_specs": {
                    "capacite": machine_input_raw.get("specifications", {}).get("capacite", ""),
                    "puissance": machine_input_raw.get("specifications", {}).get("puissance", ""),
                    "dimensions": machine_input_raw.get("specifications", {}).get("dimensions", {}),
                    "poids": machine_input_raw.get("specifications", {}).get("poids", ""),
                    "alimentation": machine_input_raw.get("specifications", {}).get("alimentation", ""),
                },
            }

            tco_suppliers = []
            if top_supplier:
                tco_suppliers.append({
                    "supplier_name": top_supplier.get("supplier_name", "Unknown"),
                    "website": top_supplier.get("website", ""),
                    "region": top_supplier.get("region", "Global"),
                    "price_estimate": top_supplier.get("price_estimate"),
                    "lead_time_days": None,
                    "source": top_supplier.get("source", "Module 4 Enrichment"),
                    "notes": top_supplier.get("notes", ""),
                    "relevance_score": top_supplier.get("relevance_score", 0),
                })

            machine_tco = tco_calculator.calculate_machine_tco(
                machine_input=tco_machine_input,
                suppliers=tco_suppliers,
                use_llm=True,
            )
            all_machine_tcos.append(machine_tco)

        products = stage_3.get("produits_fabriques", [])
        if isinstance(products, dict):
            products = products.get("produits_fabriques", [])
        if products:
            avg_machine_annual = 0
            if all_machine_tcos:
                avg_machine_annual = sum(m.annual_tco for m in all_machine_tcos) / max(len(all_machine_tcos), 1)

            for product in products:
                nom_produit = product.get("nom_produit", "Unknown")
                categorie = product.get("categorie", "finished")

                landing_cost = avg_machine_annual * 0.05
                holding_cost = avg_machine_annual * 0.03
                quality_cost = avg_machine_annual * 0.02
                administrative_cost = avg_machine_annual * 0.01

                all_product_tcos.append(ProductTCO(
                    nom_produit=nom_produit,
                    categorie=categorie,
                    landing_cost=round(landing_cost, 2),
                    holding_cost=round(holding_cost, 2),
                    quality_cost=round(quality_cost, 2),
                    administrative_cost=round(administrative_cost, 2),
                    total_tco=round(landing_cost + holding_cost + quality_cost + administrative_cost, 2),
                ))

        raw_material_tcos = []
        matieres = stage_2.get("matieres_premieres", [])
        if isinstance(matieres, dict):
            raw_materials = matieres.get("matieres_premieres", [])
        elif isinstance(matieres, list):
            raw_materials = matieres
        else:
            raw_materials = []

        if raw_materials:
            raw_material_results = tco_calculator.estimate_raw_material_costs(raw_materials, use_llm=True)
            for rm in raw_material_results:
                raw_material_tcos.append(RawMaterialTCO(**rm))

        annual_tco = tco_calculator.calculate_annual_tco(
            machine_tcos=all_machine_tcos,
            product_tcos=all_product_tcos,
            raw_material_tcos=raw_material_tcos,
            years=5,
        )

        total_machines_tco = sum(m.total_tco for m in all_machine_tcos)
        total_products_tco = sum(p.total_tco for p in all_product_tcos)
        total_raw_materials_tco = sum(r.total_tco for r in raw_material_tcos)
        total_tco = total_machines_tco + total_products_tco + total_raw_materials_tco

        info_generales = stage_1.get("informations_generales", {})
        company_name = info_generales.get("nom_entreprise", ribif_metadata.get("company_name", "Unknown Company"))
        project_name = info_generales.get("nom_projet", ribif_metadata.get("project_name", "Unknown Project"))

        result = {
            "company_name": company_name,
            "project_name": project_name,
            "calculation_date": str(date.today()),
            "total_tco": round(total_tco, 2),
            "average_annual_tco": round(total_tco / 5, 2),
            "tco_per_unit_revenue": 0,
            "machine_tco": [m.model_dump() for m in all_machine_tcos],
            "total_machines_tco": round(total_machines_tco, 2),
            "product_tco": [p.model_dump() for p in all_product_tcos],
            "total_products_tco": round(total_products_tco, 2),
            "raw_materials_tco": [r.model_dump() for r in raw_material_tcos],
            "total_raw_materials_tco": round(total_raw_materials_tco, 2),
            "annual_tco": [a.model_dump() for a in annual_tco],
            "stage_1_informations_generales": stage_1,
            "stage_2_matieres_premieres": stage_2,
            "stage_3_produits_fabriques": stage_3,
            "stage_4_machines_equipements": stage_4,
            "stage_5_processus_production": stage_5,
            "stage_6_informations_complementaires": stage_6,
            "sourcing_metadata": ribif_metadata,
        }

        if project_id:
            result["project_id"] = project_id

        output_file = OUTPUT_DIRS["module6"] / "module_6_tco.json"
        write_json(output_file, result)

        tco_run_id = None
        client = get_supabase()
        owner_id = get_request_user_id()
        if client and project_id:
            try:
                tco_run_id = insert_tco_run(client, project_id, module4_id, result)
                if tco_run_id:
                    insert_tco_details(client, tco_run_id, result)
                if output_file.exists():
                    output_file_id, output_file_url = upload_and_register_file(
                        client=client,
                        project_id=project_id,
                        owner_id=owner_id,
                        local_path=str(output_file),
                        category="module6-output",
                        label=output_file.name,
                    )
                    result.setdefault("sourcing_metadata", {})
                    result["sourcing_metadata"]["module6_output_file_id"] = output_file_id
                    result["sourcing_metadata"]["module6_output_file_url"] = output_file_url
            except Exception:
                pass

        if tco_run_id:
            result["tco_run_id"] = tco_run_id

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500


@bp_module6.route("/api/module6/tco", methods=["POST"])
def calculate_tco():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        if "machine_input" not in data:
            return jsonify({"error": "Missing required field: machine_input"}), 400
        tco_calculator = RIBIFModule6TCO()
        result = tco_calculator.process_input(data)
        if "error" in result:
            return jsonify(result), 400
        return jsonify({"message": "TCO calculated successfully", "data": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
