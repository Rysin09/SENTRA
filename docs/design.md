# SENTRA — Product & UI Design

## Design Objective
Create a calm, trustworthy, government-grade operational tool. Never sensationalize distress.

## Principles
- Human authority is visually primary.
- AI output is clearly marked as assistance.
- Avoid diagnostic language.
- Minimize personal information.
- Show confidence and limitations.
- Make missing information visible.
- Make reviewer override obvious.
- Never expose hidden chain-of-thought.

## Streamlit Pages

### 1. Case Intake
- Case ID
- Consent acknowledgement
- Text input
- Optional audio upload
- Context fields
- Submit

### 2. Processing
Show high-level stages:
1. Validating input
2. Processing voice
3. Extracting indicators
4. Combining available signals
5. Generating screening summary
6. Applying safety rules

### 3. Screening Summary
Show:
- Operational category
- Confidence
- Modalities used
- Data quality
- Eight dimensions
- Supporting indicators
- Missing signals
- Safety flags
- Human review status

### 4. Human Review
Actions:
- Review
- Override category
- Request additional information
- Add reviewer note
- Save review

### 5. Case History
Show authorized records with case ID, timestamp, status, category, confidence and review status.

## Example Card
```text
Operational Screening Category
HIGH

Confidence
0.84

Human Review
REQUIRED

Supporting Indicators
- Immediate threat language detected
- Limited support availability
- Elevated urgency indicators

Data Used
✓ Text
✓ Voice transcript
✓ Context

AI-assisted screening only.
Final assessment remains with authorized human personnel.
```

## UX Safety
Never display:
- "You have PTSD"
- "You are mentally ill"
- "You are definitely unsafe"
- "Police have been notified automatically"

Prefer:
- "Potentially elevated indicator"
- "Human review required"
- "Insufficient data for reliable screening"

## Visualization
Prefer neutral cards, compact indicators and tables. Avoid dramatic warning animations, fear-inducing imagery, excessive red, gamification and fake precision.
