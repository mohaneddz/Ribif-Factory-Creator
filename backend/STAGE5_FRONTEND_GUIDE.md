# Stage 5 API Response Structure - Frontend Integration Guide

## Overview
Module 1 Stage 5 (Processus de Production) now returns a hierarchical structure with multiple views for different display needs.

## New Response Structure

```typescript
interface Stage5ProcessusProduction {
  // KPI metrics (unchanged)
  kpi_production: {
    oee_cible: string;
    trs_cible: string;
    taux_rebut_acceptable: string;
    temps_changement_serie: string;
  };
  
  // NEW: Nested hierarchy (source of truth)
  processes: ProductProcess[];
  
  // NEW: Flattened UI view with metadata
  ui_steps: UIStep[];
  
  // NEW: Counts
  total_steps: number;        // Total across all product families
  total_ui_steps: number;     // Length of ui_steps (same as total_steps)
  total_groups: number;       // Number of product families
  
  // Backward compatible: alias to ui_steps
  processus_production: UIStep[];  // Same as ui_steps
  steps_view: "ui_flattened";
}

interface ProductProcess {
  product_family: string;     // e.g., "SPC flooring", "Injection parts"
  group_id: string;           // e.g., "group_1", "group_2"
  steps: ProcessStep[];
}

interface ProcessStep {
  nom_etape: string;          // Step name (without product prefix)
  numero_etape: number;       // Step number within this product family
  type_operation?: string;
  description?: string;
  machine?: string;
  machines_utilisees?: string[];
  inputs?: string[];
  outputs?: string[];
  qc?: string;
  parametres_process: NormalizedParameters;
}

interface UIStep extends ProcessStep {
  group_id: string;           // Which product family/group
  product_family: string;     // Product family name
  local_step_no: number;      // Step number within group (resets per group)
  global_step_no: number;     // Monotonic step number across all groups
  nom_etape: string;          // Prefixed with "[product_family] " for display
}

interface NormalizedParameters {
  temperature: ParameterValue;
  pressure: ParameterValue;
  cycle_time: ParameterValue;
  cycle_mode?: "continuous" | "sampling" | "variable" | "batch";
  speed?: ParameterValue;
  tolerances?: string;
}

interface ParameterValue {
  value: number | null;
  unit: string | null;
  source: "document_extracted" | "estimated" | "llm_generated" | "unknown";
  confidence: "high" | "medium" | "low" | "unknown";
}
```

## Usage Examples

### Example 1: Flat List Display (Minimal Change)
Use `processus_production` as before:

```typescript
const steps = data.stage_5_processus_production.processus_production;

steps.forEach(step => {
  console.log(`${step.global_step_no}. ${step.nom_etape}`);
  // nom_etape already includes [product_family] prefix
  
  const temp = step.parametres_process.temperature;
  if (temp.value !== null) {
    console.log(`  Temperature: ${temp.value}${temp.unit}`);
    console.log(`  Confidence: ${temp.confidence}`);
  }
});
```

**Output:**
```
1. [SPC flooring] Extrusion
  Temperature: 180°C
  Confidence: high
2. [SPC flooring] Cooling
  Temperature: 25°C
  Confidence: medium
3. [Injection parts] Injection
  Temperature: 200°C
  Confidence: high
```

### Example 2: Grouped Display by Product Family
Use `processes` for nested display:

```typescript
const processes = data.stage_5_processus_production.processes;

processes.forEach(process => {
  console.log(`\n=== ${process.product_family} ===`);
  console.log(`Steps: ${process.steps.length}`);
  
  process.steps.forEach(step => {
    console.log(`  ${step.numero_etape}. ${step.nom_etape}`);
    // nom_etape does NOT have product prefix here
    
    if (step.machine) {
      console.log(`     Machine: ${step.machine}`);
    }
  });
});
```

**Output:**
```
=== SPC flooring ===
Steps: 2
  1. Extrusion
     Machine: Extruder Line
  2. Cooling
     Machine: Cooling System

=== Injection parts ===
Steps: 1
  1. Injection
     Machine: Injection Press
```

### Example 3: UI Steps with Group Metadata
Use `ui_steps` for detailed flat display with grouping info:

```typescript
const uiSteps = data.stage_5_processus_production.ui_steps;
const totalGroups = data.stage_5_processus_production.total_groups;
const totalSteps = data.stage_5_processus_production.total_steps;

console.log(`Total: ${totalSteps} steps across ${totalGroups} product families\n`);

let currentGroup = null;

uiSteps.forEach(step => {
  // Show group header when group changes
  if (step.group_id !== currentGroup) {
    console.log(`\n--- ${step.product_family} ---`);
    currentGroup = step.group_id;
  }
  
  console.log(`Step ${step.global_step_no} (${step.local_step_no} in group): ${step.nom_etape}`);
});
```

**Output:**
```
Total: 3 steps across 2 product families

--- SPC flooring ---
Step 1 (1 in group): [SPC flooring] Extrusion
Step 2 (2 in group): [SPC flooring] Cooling

--- Injection parts ---
Step 3 (1 in group): [Injection parts] Injection
```

### Example 4: Display Parameters with Units
```typescript
function formatParameter(param: ParameterValue): string {
  if (param.value === null) {
    return "N/A";
  }
  return `${param.value}${param.unit || ""} (${param.confidence})`;
}

steps.forEach(step => {
  const params = step.parametres_process;
  
  console.log(`\n${step.nom_etape}`);
  console.log(`  Temperature: ${formatParameter(params.temperature)}`);
  console.log(`  Pressure: ${formatParameter(params.pressure)}`);
  console.log(`  Cycle Time: ${formatParameter(params.cycle_time)}`);
  
  if (params.cycle_mode) {
    console.log(`  Cycle Mode: ${params.cycle_mode}`);
  }
});
```

**Output:**
```
[SPC flooring] Extrusion
  Temperature: 180°C (high)
  Pressure: 5bar (medium)
  Cycle Time: 45s (medium)

[SPC flooring] Cooling
  Temperature: 25°C (medium)
  Pressure: N/A
  Cycle Time: N/A
  Cycle Mode: continuous
```

## UI Component Suggestions

### Card-Based Display
```jsx
// For flat display with product badges
<div className="steps-list">
  {data.processus_production.map(step => (
    <Card key={step.global_step_no}>
      <CardHeader>
        <Badge>{step.product_family}</Badge>
        <StepNumber>{step.global_step_no}</StepNumber>
        <Title>{step.nom_etape.replace(/^\[.*?\]\s*/, '')}</Title>
      </CardHeader>
      <CardBody>
        {step.machine && <Machine>{step.machine}</Machine>}
        <Parameters>
          {step.parametres_process.temperature.value && (
            <Param>
              <Label>Temperature</Label>
              <Value>
                {step.parametres_process.temperature.value}
                {step.parametres_process.temperature.unit}
              </Value>
              <Confidence level={step.parametres_process.temperature.confidence} />
            </Param>
          )}
          {/* Repeat for pressure, cycle_time, etc. */}
        </Parameters>
      </CardBody>
    </Card>
  ))}
</div>
```

### Grouped Accordion Display
```jsx
// For grouped display by product family
<div className="process-groups">
  {data.processes.map(process => (
    <Accordion key={process.group_id}>
      <AccordionHeader>
        <h3>{process.product_family}</h3>
        <Badge>{process.steps.length} steps</Badge>
      </AccordionHeader>
      <AccordionBody>
        {process.steps.map(step => (
          <StepItem key={step.numero_etape}>
            <StepNumber>{step.numero_etape}</StepNumber>
            <StepName>{step.nom_etape}</StepName>
            {/* Parameters, machine, etc. */}
          </StepItem>
        ))}
      </AccordionBody>
    </Accordion>
  ))}
</div>
```

### Table Display
```jsx
// For compact table view
<table>
  <thead>
    <tr>
      <th>Step #</th>
      <th>Product</th>
      <th>Operation</th>
      <th>Machine</th>
      <th>Temp</th>
      <th>Pressure</th>
      <th>Cycle</th>
    </tr>
  </thead>
  <tbody>
    {data.ui_steps.map(step => (
      <tr key={step.global_step_no}>
        <td>{step.global_step_no}</td>
        <td>{step.product_family}</td>
        <td>{step.nom_etape.replace(/^\[.*?\]\s*/, '')}</td>
        <td>{step.machine || '-'}</td>
        <td>
          {step.parametres_process.temperature.value 
            ? `${step.parametres_process.temperature.value}${step.parametres_process.temperature.unit}`
            : '-'
          }
        </td>
        <td>
          {step.parametres_process.pressure.value
            ? `${step.parametres_process.pressure.value}${step.parametres_process.pressure.unit}`
            : '-'
          }
        </td>
        <td>
          {step.parametres_process.cycle_mode || 
           (step.parametres_process.cycle_time.value
             ? `${step.parametres_process.cycle_time.value}${step.parametres_process.cycle_time.unit}`
             : '-'
           )
          }
        </td>
      </tr>
    ))}
  </tbody>
</table>
```

## Summary Displays

### Step Count Display
```typescript
// Show accurate counts
const { total_steps, total_groups } = data.stage_5_processus_production;

if (total_groups > 1) {
  console.log(`${total_steps} étapes au total (${total_groups} lignes de produits)`);
} else {
  console.log(`${total_steps} étapes de production`);
}

// DON'T show inflated counts like "57 étapes" when it's actually 34
```

### Group Summary
```typescript
data.processes.forEach(process => {
  console.log(`${process.product_family}: ${process.steps.length} étapes`);
});
```

## Migration Checklist

- [ ] Update Stage 5 display component
- [ ] Use `ui_steps` or `processes` instead of old flat list
- [ ] Display parameter values with units from structured objects
- [ ] Show confidence levels for critical parameters
- [ ] Handle multiple product families (if `total_groups > 1`)
- [ ] Display accurate step counts using `total_steps`
- [ ] Test with both enriched (nested) and extraction-only (flat) data
- [ ] Handle null parameter values gracefully
- [ ] Show cycle_mode for continuous processes

## Notes

1. **Backward Compatibility**: `processus_production` still works as before, but now includes group metadata
2. **Step Numbering**: 
   - `global_step_no`: Use for flat display (1, 2, 3, ...)
   - `local_step_no`: Use for grouped display (resets per group: 1, 2, 1, 2, ...)
3. **Parameter Nulls**: Always check `value !== null` before displaying
4. **Confidence Levels**: Consider styling based on confidence (high=green, medium=yellow, low=red)
5. **Product Prefix**: In `ui_steps`, `nom_etape` includes `[product_family]` prefix; in `processes[].steps`, it doesn't

## Questions?

- See backend implementation: `utils/module_1/stage5_utils.py`
- See tests: `test_module1_stage5.py`
- See full summary: `STAGE5_FIX_SUMMARY.md`
