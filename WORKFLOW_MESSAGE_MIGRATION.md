# WorkflowMessage Migration Plan

## 개요
모든 executor 간 통신을 통일된 `WorkflowMessage` 인터페이스로 변경

## 변경 사항

### 1. 새로운 모델: `WorkflowMessage`

```python
class WorkflowMessage(BaseModel):
    # Core
    question: str
    database: str
    sql: Optional[str]
    status: Literal["Init", "SchemaSelected", "SQLGenerated", "Success", "SyntaxError", "SemanticError", "EmptyResult", "Timeout"]
    
    # Results
    result_rows: Optional[List[Dict]]
    error_message: Optional[str]
    
    # Metadata
    retry_context: RetryContext  # Included (no shared state lookup needed)
    confidence: Optional[float]
    reasoning: Optional[str]
    selected_tables: Optional[List[str]]
    
    # References
    schema_id: Optional[str]  # Reference to detailed schema in shared state
    
    # Metrics
    execution_time_ms: float
    row_count: int
```

### 2. Status 흐름

```
Init 
  → (initialize_context)
SchemaSelected 
  → (schema_understanding)
SQLGenerated 
  → (sql_generation)
Success / SyntaxError / SemanticError / EmptyResult / Timeout
  → (switch-case routing)
```

### 3. Shared State 최소화

**이전 (많은 shared state 접근)**:
- `CURRENT_QUESTION_KEY` - 모든 executor가 접근
- `RETRY_CONTEXT_KEY` - 모든 error handler가 접근
- `CURRENT_SQL_RESPONSE_KEY` - 여러 executor가 접근
- ... 등등

**이후 (메시지에 포함)**:
- `question` - WorkflowMessage에 포함
- `retry_context` - WorkflowMessage에 포함
- `sql`, `confidence`, `reasoning` - WorkflowMessage에 포함

**여전히 shared state 사용 (대용량 데이터)**:
- `M_SCHEMA_CACHE_KEY` - 전체 M-Schema (한번만 로드)
- `SCHEMA_STATE_PREFIX + schema_id` - 상세 스키마 (CREATE TABLE 등)
- `RETURN_NL_KEY` - Flag (자주 접근 안함)

### 4. Executor별 변경사항

#### ✅ initialize_context
- **입력**: `NL2SQLInput` (workflow input)
- **출력**: `WorkflowMessage(status="Init")`
- **변경**: 
  - M-Schema와 RETURN_NL만 shared state에 저장
  - 나머지는 WorkflowMessage로 전달

#### ✅ schema_understanding
- **입력**: `WorkflowMessage(status="Init" or "SemanticError")`
- **출력**: `WorkflowMessage(status="SchemaSelected")`
- **변경**: 
  - Message에서 question, database 추출
  - M-Schema를 shared state에서 가져와서 prompt 생성
  - 결과를 WorkflowMessage로 전달

#### ✅ sql_generation
- **입력**: `WorkflowMessage(status="SchemaSelected" or "SyntaxError")`
- **출력**: `WorkflowMessage(status=Success/Error/*)`
- **변경**: 
  - Message에서 question, schema_id 추출
  - 상세 스키마를 shared state에서 가져와서 prompt 생성
  - 실행 결과를 WorkflowMessage로 전달

#### 🔄 handle_syntax_error (TODO)
- **입력**: `WorkflowMessage(status="SyntaxError")`
- **출력**: `WorkflowMessage(status="SyntaxError")` (retry용)
- **변경**:
  - Message에서 retry_context 가져옴 (shared state 불필요!)
  - 재시도 가능 여부 확인
  - 수정된 retry_context와 함께 WorkflowMessage 전송

#### 🔄 handle_semantic_error (TODO)
- **입력**: `WorkflowMessage(status="SemanticError")`
- **출력**: `WorkflowMessage(status="SemanticError")` (retry용)
- **변경**:
  - Message에서 retry_context 가져옴
  - 재시도 가능 여부 확인
  - 수정된 retry_context와 함께 WorkflowMessage 전송

#### 🔄 handle_success (TODO)
- **입력**: `WorkflowMessage(status="Success")`
- **출력**: `WorkflowMessage` (fan-out to parallel executors)
- **변경**:
  - Message에 모든 정보 포함되어 있음
  - Shared state 접근 최소화

#### 🔄 evaluate_sql_reasoning (TODO)
- **입력**: `WorkflowMessage(status="Success")`
- **출력**: `ReasoningEvaluation` or similar
- **변경**:
  - Message에서 question, sql, reasoning, result_rows 추출

#### 🔄 generate_natural_language_response (TODO)
- **입력**: `WorkflowMessage(status="Success")`
- **출력**: `str` (NL response)
- **변경**:
  - Message에서 question, result_rows 추출

#### 🔄 aggregate_success_results (TODO)
- **입력**: `list[Any]` (fan-in from parallel executors)
- **출력**: `NL2SQLOutput`
- **변경**:
  - 첫 번째 WorkflowMessage에서 기본 정보 추출
  - 병렬 executor 결과들 aggregate

### 5. 장점

✅ **타입 일관성**: 모든 `send_message` 호출이 동일한 타입
✅ **Shared state 접근 감소**: question, retry_context 등이 메시지에 포함
✅ **디버깅 쉬움**: 메시지만 보면 전체 상태 파악 가능
✅ **확장성**: 새 필드 추가 용이
✅ **명확한 데이터 흐름**: 메시지 = 작은 상태, Shared state = 큰 데이터

### 6. 마이그레이션 체크리스트

- [x] WorkflowMessage 모델 정의
- [x] workflow.py 업데이트 (switch-case condition)
- [x] initialize_context 변경
- [x] schema_understanding 변경
- [x] sql_generation 변경
- [x] handle_syntax_error 변경
- [x] handle_semantic_error 변경
- [x] handle_execution_issue 변경
- [x] handle_success 변경
- [x] evaluate_sql_reasoning 변경
- [x] generate_natural_language_response 변경
- [x] aggregate_success_results 변경
- [ ] 테스트 및 검증

### 7. 주요 변경사항 요약

#### ✅ 완료된 리팩토링 (12/12 executors - 100% 완료!)

**✅ 핵심 워크플로우 경로**:
- `initialize_context`: NL2SQLInput → WorkflowMessage(status="Init")
- `schema_understanding`: WorkflowMessage → WorkflowMessage(status="SchemaSelected")
- `sql_generation`: WorkflowMessage → WorkflowMessage(status=Success/Error/*)
  
**✅ 에러 처리 경로**:
- `handle_syntax_error`: WorkflowMessage(SyntaxError) → WorkflowMessage(retry)
- `handle_semantic_error`: WorkflowMessage(SemanticError) → WorkflowMessage(retry)
- `handle_execution_issue`: WorkflowMessage → NL2SQLOutput (terminal)

**✅ 성공 경로 (Fan-out/Fan-in)**:
- `handle_success`: WorkflowMessage(Success) → WorkflowMessage (fan-out dispatcher)
- `evaluate_sql_reasoning`: WorkflowMessage → dict (parallel executor)
- `generate_natural_language_response`: WorkflowMessage → str|None (parallel executor)
- `aggregate_success_results`: list[dict|str|None] → NL2SQLOutput (fan-in aggregator)

#### 주요 개선사항

1. **Shared State 접근 감소**:
   - Before: 모든 executor가 CURRENT_QUESTION_KEY, RETRY_CONTEXT_KEY 접근
   - After: 데이터가 WorkflowMessage에 포함됨

2. **타입 일관성**:
   - Before: `list[ChatMessage]` vs `ExecutionResult` 혼재
   - After: 모든 주요 executor 간 통신이 `WorkflowMessage` 사용
   - Fan-in executors는 return 값으로 dict/str 전달 (framework 지원)

3. **Retry 로직 간소화**:
   ```python
   # Before
   retry_ctx_dict = await ctx.get_shared_state(RETRY_CONTEXT_KEY)
   retry_ctx = RetryContext(**retry_ctx_dict)
   if not retry_ctx.can_retry_syntax():
       ...
   
   # After
   if not message.can_retry_syntax():
       ...
   ```

4. **에러 처리 개선**:
   - 모든 에러 정보가 WorkflowMessage에 포함
   - Retry context도 메시지와 함께 전달
   - Shared state 업데이트 불필요

5. **Fan-out/Fan-in 패턴 최적화**:
   - handle_success가 WorkflowMessage를 shared state에 저장
   - 병렬 executors가 필요한 정보만 shared state에서 가져옴
   - aggregate_success_results가 WorkflowMessage 복원

### 8. Breaking Changes

⚠️ **Executor 시그니처 변경**:
```python
# Before
async def my_executor(messages: list[ChatMessage], ctx: WorkflowContext) -> None:

# After
async def my_executor(message: WorkflowMessage, ctx: WorkflowContext[WorkflowMessage]) -> None:
```

⚠️ **Switch-case condition 변경**:
```python
# Before
get_execution_status_condition("Success")  # checks ExecutionResult

# After  
get_execution_status_condition("Success")  # checks WorkflowMessage
```
