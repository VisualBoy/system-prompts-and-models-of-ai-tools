from pydantic import BaseModel, Field, ValidationError, root_validator
from typing import List, Dict, Optional, Any
from multiprocessing import Process
import os
import time

# --- Pydantic Data Models for Pipeline ---

// Assume HFT-specific tool handlers ('FetchMarketDataHFT', 'ExecuteOrderHFT', 'ConditionalLogic')
// and Proto schemas are registered in a bootstrap phase available to workers.

class MarketData(BaseModel):
    instrument: str
    ask: float

class OrderConfirmation(BaseModel):
    exec_status: str
    instrument: str
    price: float

class PipelineStep(BaseModel):
    tool: str
    input_map: Dict[str, Any]
    params: Optional[Dict[str, Any]] = None
    condition_true_only: Optional[bool] = False

class PipelineOptions(BaseModel):
    overall_timeout_ms: int = 150
    fail_fast: bool = True

class PipelineInput(BaseModel):
    target_instrument: str
    client_order_id: str
    buy_price_threshold: float

class PipelineResult(BaseModel):
    success: bool
    output: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None

    def get_output_of_step(self, step: str) -> Optional[dict]:
        return self.output.get(step)

# --- Agent Pattern for Orchestration ---

class HFTPipelineAgent:
    def __init__(self, initial_data: PipelineInput, pipeline_def: List[PipelineStep], options: PipelineOptions):
        self.initial_data = initial_data
        self.pipeline_def = pipeline_def
        self.options = options
        self.context = {'initial': initial_data.dict()}

    def fetch_market_data(self, instrument: str) -> MarketData:
        # Simulate market data
        return MarketData(instrument=instrument, ask=1.07480)

    def conditional_logic(self, ask: float, buy_price_threshold: float, operator: str) -> bool:
        if operator == 'lt':
            return ask < buy_price_threshold
        raise NotImplementedError("Only 'lt' operator supported in this example.")

    def execute_order(self, instrument: str, price: float) -> OrderConfirmation:
        # Simulate order execution
        return OrderConfirmation(exec_status='FILLED', instrument=instrument, price=price)

    def run(self) -> PipelineResult:
        try:
            for step in self.pipeline_def:
                if step.tool == 'FetchMarketDataHFT':
                    data = self.fetch_market_data(self.context['initial']['target_instrument'])
                    self.context['FetchMarketDataHFT'] = data.dict()
                elif step.tool == 'ConditionalLogic':
                    ask = self.context['FetchMarketDataHFT']['ask']
                    threshold = self.context['initial']['buy_price_threshold']
                    operator = step.params['operator']
                    condition = self.conditional_logic(ask, threshold, operator)
                    self.context['ConditionalLogic'] = {'condition': condition}
                    if not condition and step.condition_true_only:
                        return PipelineResult(success=True, output={})
                elif step.tool == 'ExecuteOrderHFT':
                    if step.condition_true_only and not self.context['ConditionalLogic']['condition']:
                        continue
                    instrument = self.context['FetchMarketDataHFT']['instrument']
                    price = self.context['FetchMarketDataHFT']['ask']
                    order = self.execute_order(instrument, price)
                    self.context['ExecuteOrderHFT'] = order.dict()
            return PipelineResult(success=True, output={'ExecuteOrderHFT': self.context.get('ExecuteOrderHFT')})
        except Exception as e:
            return PipelineResult(success=False, error_message=str(e))

# --- Worker and Supervisor Logic ---

def hft_pipeline_worker_main(worker_id: int):
    pid = os.getpid()
    print(f"[HFTPipelineWorker {worker_id} PID: {pid}] Started. Ready for HFT pipeline execution.")

    initial_data = PipelineInput(
        target_instrument='EURUSD_FX',
        client_order_id=f"W{worker_id}_ORD_{int(time.time())}",
        buy_price_threshold=1.07500
    )
    pipeline_def = [
        PipelineStep(tool='FetchMarketDataHFT', input_map={'instrument': '@initial.target_instrument'}),
        PipelineStep(
            tool='ConditionalLogic',
            input_map={'condition_field_path': '@previous.ask', 'value_to_compare': '@initial.buy_price_threshold'},
            params={'operator': 'lt'}
        ),
        PipelineStep(
            tool='ExecuteOrderHFT',
            condition_true_only=True,
            input_map={'instrument': '@FetchMarketDataHFT.instrument', 'trade_side': 'BUY', 'limit_price': '@FetchMarketDataHFT.ask'}
        ),
    ]
    options = PipelineOptions()

    agent = HFTPipelineAgent(initial_data, pipeline_def, options)
    result = agent.run()
    if result.success:
        order_conf = result.get_output_of_step("ExecuteOrderHFT")
        if order_conf:
            print(f"[HFTPipelineWorker {worker_id}] Order Result: {order_conf.get('exec_status', 'N/A')}")
        else:
            print(f"[HFTPipelineWorker {worker_id}] Order condition not met or no order placed.")
    else:
        print(f"[HFTPipelineWorker {worker_id}] HFT Pipeline Error: {result.error_message}")
    print(f"[HFTPipelineWorker {worker_id} PID: {pid}] HFT task cycle finished.")

def supervisor(num_workers: int = 2):
    print("[Master Supervisor] Starting HFTPipelineCluster with expert settings...")
    workers = []
    for worker_id in range(num_workers):
        p = Process(target=hft_pipeline_worker_main, args=(worker_id,))
        p.start()
        print(f"[Master] HFT Worker {worker_id} (PID {p.pid}) started.")
        workers.append((worker_id, p))
    for worker_id, p in workers:
        p.join(timeout=10)
        print(f"[Master] HFT Worker {worker_id} (PID {p.pid}) exited. ExitCode:{p.exitcode}")
    print("[Master Supervisor] Orchestration ended normally.")

if __name__ == "__main__":
    supervisor(num_workers=2)
