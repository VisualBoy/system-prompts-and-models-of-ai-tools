from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

# ------------------------------------------------------------------------------
# This script initiates a pipeline to plan a new frontend module.
# It leverages automated topic extraction for GraphRAG, fetches comprehensive context,
# and then consults a specialized "Intelligent Intern" agent trained for module development.
# Assumes the PipelineOrchestrator and tool handlers (ExtractTopicsFromRequest, GenerateText_ModuleDevIntern)
# are configured in the application's bootstrap phase.
# Automated context logging to a graph database is also assumed to be active.
# ------------------------------------------------------------------------------

# --- Pydantic Models ---

class InitialData(BaseModel):
    user_coding_task: str = Field(..., description="User's main coding request")
    project_identifier: str

class ExtractTopicsOutput(BaseModel):
    extracted_topics: List[str]

class GenerateTextModuleDevInternParams(BaseModel):
    use_graph_context: bool = True  # Enable GraphRAG.
    # For GraphRAG context_topics:
    # The 'topics_from_previous_step_output' in the 'GenerateText_ModuleDevIntern'
    # tool handler configuration (set during bootstrap) will automatically use the 'extracted_topics'
    # from the 'ExtractTopicsFromRequest' step.
    context_depth: str = "auto"  # This is a special instruction to the GraphRAGAgent
    # (configured in the 'GenerateText_ModuleDevIntern' tool handler).
    # It signifies that the agent should retrieve a comprehensive context related to the
    # extracted topics (e.g., "frontend module", "user profile"). This involves fetching
    # all relevant information the system has ever stored and linked regarding module
    # construction, best practices, previously programmed modules, relevant Vue 3/Pinia patterns,
    # and any specific guidance previously given to or learned by "intern" agents.
    # The GraphRAGAgent translates "auto" into an extensive graph query.
    max_context_tokens: int = 2000  # Allow a larger context for coding tasks.
    # 'model_identifier': 'intern_v2' # Optionally specify a version of the intern agent.
    llm_options: Dict[str, Any] = {"guidance_level": "detailed"}  # Custom options for the intern.

class PipelineStep(BaseModel):
    tool: str
    input_map: Dict[str, str]
    params: Optional[Dict[str, Any]] = None

class InternOutput(BaseModel):
    module_plan: Optional[str]
    important_notes: Optional[List[str]]

# --- Simulated Pipeline Orchestrator Result ---

class Result(BaseModel):
    success: bool
    final_output: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    failed_step_info: Optional[Dict[str, Any]] = None

    def is_success(self):
        return self.success

    def get_final_output(self):
        return self.final_output

    def get_error_message(self):
        return self.error_message

    def get_failed_step_details(self):
        return self.failed_step_info

# --- Simulated Pipeline Runner Function ---
def run_pipeline(initial_data: InitialData, pipeline_definition: List[PipelineStep]) -> Result:
    # Stub function for orchestration logic
    # Implement tool handler logic as needed
    # Output of the last step (GenerateText_ModuleDevIntern)
    return Result(success=True, final_output={
        "module_plan": "Example plan structure...",
        "important_notes": ["Note 1", "Note 2"]
    })

# ------------------------------------------------------------------------------
# Initial data for the pipeline, primarily the user's request.
user_coding_request = (
    "We want to build a new frontend module for user profile management. "
    "It should include features for editing personal details, managing notification preferences, "
    "and viewing activity logs."
)

initial_data = InitialData(
    user_coding_task=user_coding_request,
    project_identifier="project_alpha"
)

# ------------------------------------------------------------------------------
# Pipeline definition, mapping steps and parameters.
pipeline_definition = [
    PipelineStep(
        tool="ExtractTopicsFromRequest",
        # The orchestrator will automatically take initialData (if string) or a specified field
        # from initialData as input if 'input_map' is simple or by convention.
        # Here, we explicitly map it for clarity.
        input_map={"text_input": "@initial.user_coding_task"}
        # Output of this step will be e.g., { "extracted_topics": ["frontend module", "user profile", "Vue 3", "Pinia"] }
    ),
    PipelineStep(
        tool="GenerateText_ModuleDevIntern",  # Call the specialized "Intelligent Intern" for module development
        input_map={
            # The main user request is passed directly to the intern.
            "user_request": "@initial.user_coding_task",
            "project_id": "@initial.project_identifier"
        },
        params=GenerateTextModuleDevInternParams().dict()
    )
]

# ------------------------------------------------------------------------------
print(f'Starting frontend module planning pipeline for request: "{user_coding_request}"')
result = run_pipeline(initial_data, pipeline_definition)

if result.is_success():
    print("\nIntelligent Intern (Module Development) Response:")
    intern_output = result.get_final_output()  # Output of the last step (GenerateText_ModuleDevIntern)

    print("Suggested Module Plan / Code Structure:")
    print("----------------------------------------")
    print(intern_output.get("module_plan", "No plan generated."))
    print("----------------------------------------")

    if intern_output.get("important_notes"):
        print("\nKey Considerations:")
        for note in intern_output["important_notes"]:
            print(f"- {note}")

    # --------------------------------------------------------------------------
    # The context used by the Intelligent Intern was automatically built by:
    # 1. The 'ExtractTopicsFromRequest' step identifying key concepts.
    # 2. The 'GenerateText_ModuleDevIntern' tool's RAG configuration (defined during bootstrap)
    #    triggering the GraphRAGAgent.
    # 3. The GraphRAGAgent using the extracted topics and 'context_depth: "auto"' to perform
    #    an extensive query against the graph database. This database contains knowledge
    #    from all previous interactions, documentation, and specific training given to interns
    #    regarding module development (e.g., hints on Vue 3, Pinia, common pitfalls,
    #    architectural patterns from past module programming tasks).
    # 4. This rich, dynamically retrieved context was then provided to the
    #    "IntelligentIntern_ModuleDevelopment" agent to enrich its planning process for the new module.
    # 5. All interactions (this pipeline run, its steps, inputs, outputs) are typically automatically
    #    logged to the graph database by the PipelineOrchestrator's auto-context logging feature
    #    (if enabled during bootstrap), further enriching the context for future tasks.
    # --------------------------------------------------------------------------
else:
    print(f"\nPipeline Error: {result.get_error_message()}")
    failed_step_info = result.get_failed_step_details()
    if failed_step_info:
        print(f"Failure occurred at step ID '{failed_step_info['step_id']}' with error: {failed_step_info['error']}")
