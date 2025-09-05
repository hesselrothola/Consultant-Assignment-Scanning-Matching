# Consultant Profile Configuration for High-Level Profiles

## Management Consultant Keywords
When scanning for assignments, prioritize these keywords for management roles:

### Titles to Match:
- **Swedish**: VD, CTO, CIO, CDO, IT-chef, Utvecklingschef, Projektledare, Programledare, Förvaltningsledare, Digitaliseringschef
- **English**: CEO, CTO, CIO, CDO, IT Manager, Development Manager, Project Manager, Program Manager, Portfolio Manager, Digital Transformation Lead

### Key Skills for Management:
- Strategic Planning / Strategisk planering
- Digital Transformation / Digital transformation
- Change Management / Förändringsledning
- Agile Leadership / Agil ledning
- Budget Responsibility / Budgetansvar
- Team Leadership / Teamledning
- Stakeholder Management / Intressenthantering

## Data Specialist Keywords
For data specialist matching:

### Titles to Match:
- **Swedish**: Dataarkitekt, Dataingenjör, BI-konsult, Dataanalytiker, ML-ingenjör, AI-specialist
- **English**: Data Architect, Data Engineer, BI Consultant, Data Analyst, ML Engineer, AI Specialist, Analytics Manager

### Key Skills for Data Specialists:
- **Platforms**: Azure Data Factory, Databricks, Snowflake, AWS Redshift, Google BigQuery
- **Tools**: Power BI, Tableau, Qlik Sense, Looker
- **Languages**: Python, SQL, R, Scala, PySpark
- **Concepts**: Data Warehouse, Data Lake, ETL/ELT, Data Governance, MDM, Data Mesh

## Seniority Level Filters
Since you have high-level consultants, the system should:

1. **Filter OUT junior positions** containing:
   - Junior, Entry-level, Graduate, Trainee
   - "0-2 års erfarenhet"
   - "Nyexaminerad"

2. **Prioritize senior positions** containing:
   - Senior, Lead, Principal, Head of, Chief
   - "10+ års erfarenhet"
   - "Omfattande erfarenhet"
   - "Ledande roll"

## Assignment Duration Preferences
High-level consultants typically prefer:
- **Minimum**: 6 months assignments
- **Optimal**: 12+ months
- **Type**: Strategic initiatives, transformations, interim leadership

## Rate Expectations
For Swedish market (2024):
- **Management Consultants**: 1,200-1,800 SEK/hour
- **Senior Data Architects**: 1,100-1,500 SEK/hour
- **BI/Analytics Leads**: 1,000-1,400 SEK/hour

## Matching Score Adjustments
For your consultant base, adjust weights to:
```
Match Score = 
  35% Semantic similarity (understand leadership/strategic terms)
  20% Seniority match (MUST be senior level)
  20% Role compatibility
  15% Domain expertise (finance, retail, public sector)
  10% Location/remote (executives often need onsite presence)
```

## Red Flags to Avoid
Automatically score LOW for assignments with:
- "Kodning krävs" (coding required) for management roles
- "Hands-on utveckling" without architectural responsibility
- Short-term (< 3 months) for senior roles
- Pure implementation without strategic component

## Green Flags to Prioritize
Score HIGH for assignments with:
- "Strategisk" / "Strategic" 
- "Transformations" / "Transformation"
- "Interim" leadership positions
- "Arkitektur" / "Architecture" for data roles
- Budget/P&L responsibility mentioned
- Board/steering committee interaction