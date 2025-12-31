"""
Insight Generator

Core insight generation engine following the architecture:
Intent → Semantic Layer → SQL → Analytics → Assembler → LLM → UI
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json
import hashlib

from src.insights.models import (
    Insight, InsightCard, InsightType, InsightSeverity,
    InsightsRequest, InsightsResponse
)
from src.connection.manager import get_connection_manager
from src.analytics.statistics import StatisticalAnalyzer
from src.analytics.anomaly import AnomalyDetector, AnomalyMethod
from src.analytics.forecasting import get_forecaster, ForecastMethod
from src.analytics.attribution import get_attribution_analyzer
from src.insights.learner import get_insight_learner
from src.llm.client import get_llm_client

logger = logging.getLogger(__name__)


class InsightGenerator:
    """
    Generates insights for database connections.
    
    Architecture:
    1. Intent Classification (what type of insights to generate)
    2. Semantic Layer (understand schema and metrics)
    3. SQL Generation (validated queries)
    4. Analytics Engine (pattern detection, attribution, forecasting)
    5. Insight Assembler (facts only, no opinions)
    6. LLM (explanation + narrative)
    7. UI (insight cards)
    """
    
    def __init__(self):
        self.manager = get_connection_manager()
        self.stats_analyzer = StatisticalAnalyzer()
        self.anomaly_detector = AnomalyDetector()
        self.forecaster = get_forecaster()
        self.attribution_analyzer = get_attribution_analyzer()
        self.learner = get_insight_learner()
        self.llm_client = get_llm_client()
    
    def generate_insights(self, request: InsightsRequest) -> InsightsResponse:
        """Generate insights for a database connection."""
        logger.info(f"Generating insights for connection {request.connection_id}")
        
        # Get connection details
        connection = self.manager.get_connection_config(request.connection_id)
        if not connection:
            raise ValueError(f"Connection {request.connection_id} not found")
        
        # Get schema for semantic layer
        schema = self.manager.get_schema(request.connection_id)
        if not schema:
            logger.info(f"Schema not cached, discovering for {request.connection_id}")
            schema = self.manager.discover_schema(request.connection_id)
        
        # Determine which insight types to generate
        insight_types = request.insight_types or list(InsightType)
        
        # Generate insights for each type
        all_insights = []
        
        if InsightType.PATTERN in insight_types:
            all_insights.extend(self._generate_pattern_insights(request, schema))
        
        if InsightType.TREND in insight_types:
            all_insights.extend(self._generate_trend_insights(request, schema))
        
        if InsightType.ANOMALY in insight_types:
            all_insights.extend(self._generate_anomaly_insights(request, schema))
        
        if InsightType.COMPARISON in insight_types:
            all_insights.extend(self._generate_comparison_insights(request, schema))
        
        if InsightType.QUALITY in insight_types:
            all_insights.extend(self._generate_quality_insights(request, schema))
        
        if InsightType.USAGE in insight_types:
            all_insights.extend(self._generate_usage_insights(request, schema))
        
        # NEW: Add forecasting insights
        if InsightType.FORECAST in insight_types:
            all_insights.extend(self._generate_forecast_insights(request, schema))
        
        # NEW: Add attribution insights
        if InsightType.ATTRIBUTION in insight_types:
            all_insights.extend(self._generate_attribution_insights(request, schema))
        
        # Calculate impact scores for all insights
        for insight in all_insights:
            age_hours = (datetime.utcnow() - insight.timestamp).total_seconds() / 3600
            score = self.learner.calculate_impact_score(
                insight_id=insight.id,
                base_confidence=insight.confidence,
                severity=insight.severity.value,
                age_hours=age_hours
            )
            insight.impact_score = score.final_score
            insight.impact_level = score.impact_level
        
        # Apply role-based filtering and prioritization
        if request.user_role:
            all_insights = self._filter_by_role(all_insights, request.user_role)
        
        # Filter by confidence and sort by impact score
        filtered_insights = [
            i for i in all_insights 
            if i.confidence >= request.min_confidence
        ]
        # Sort by impact score (highest first), then by severity
        filtered_insights.sort(
            key=lambda x: (x.impact_score or 0, x.severity.value), 
            reverse=True
        )
        filtered_insights = filtered_insights[:request.max_insights]
        
        # Convert insights to cards with LLM narratives (role-aware)
        insight_cards = []
        for insight in filtered_insights:
            narrative = self._generate_narrative(insight, user_role=request.user_role)
            actions = self._generate_actions(insight, user_role=request.user_role)
            
            card = InsightCard(
                insight=insight,
                narrative=narrative,
                suggested_actions=actions,
                related_insights=[]
            )
            insight_cards.append(card)
        
        # Generate overall summary
        summary = self._generate_summary(connection, insight_cards)
        
        return InsightsResponse(
            connection_id=request.connection_id,
            connection_name=connection.name,
            insights=insight_cards,
            analysis_summary=summary
        )
    
    def _generate_pattern_insights(self, request: InsightsRequest, schema) -> List[Insight]:
        """Detect patterns in the data."""
        insights = []
        conn = None
        
        try:
            conn = self.manager.get_connection(request.connection_id)
            
            # Pattern: Tables with rapid growth
            for table_name, table in schema.tables.items():
                if table.row_count and table.row_count > 1000:
                    insight_id = self._generate_insight_id(f"pattern-growth-{table_name}")
                    
                    insights.append(Insight(
                        id=insight_id,
                        type=InsightType.PATTERN,
                        severity=InsightSeverity.INFO,
                        title=f"Large dataset: {table_name}",
                        description=f"Table {table_name} contains {table.row_count:,} rows",
                        facts=[
                            f"Table has {table.row_count:,} total rows",
                            f"Table has {len(table.columns)} columns",
                            f"Average row size can impact query performance"
                        ],
                        metric_value=float(table.row_count),
                        metric_label="Total Rows",
                        confidence=0.95
                    ))
            
            # Pattern: Tables with many columns (wide tables)
            for table_name, table in schema.tables.items():
                if len(table.columns) > 20:
                    insight_id = self._generate_insight_id(f"pattern-wide-{table_name}")
                    
                    insights.append(Insight(
                        id=insight_id,
                        type=InsightType.PATTERN,
                        severity=InsightSeverity.LOW,
                        title=f"Wide table detected: {table_name}",
                        description=f"Table {table_name} has {len(table.columns)} columns",
                        facts=[
                            f"Table has {len(table.columns)} columns",
                            "Wide tables may benefit from normalization",
                            "Consider if all columns are frequently used together"
                        ],
                        metric_value=float(len(table.columns)),
                        metric_label="Column Count",
                        confidence=0.9
                    ))
            
        except Exception as e:
            logger.error(f"Error generating pattern insights: {e}")
        finally:
            if conn:
                self.manager.release_connection(request.connection_id, conn)
        
        return insights
    
    def _generate_trend_insights(self, request: InsightsRequest, schema) -> List[Insight]:
        """Detect trends in time-series data."""
        insights = []
        conn = None
        
        try:
            conn = self.manager.get_connection(request.connection_id)
            
            # Look for tables with date/timestamp columns
            for table_name, table in schema.tables.items():
                date_columns = [
                    col.name for col in table.columns 
                    if 'date' in col.name.lower() or 'time' in col.name.lower() 
                    or col.data_type.lower() in ['timestamp', 'date', 'datetime']
                ]
                
                if date_columns and table.row_count and table.row_count > 100:
                    # Try to analyze temporal patterns
                    date_col = date_columns[0]
                    
                    with conn.cursor() as cursor:
                        # Check data distribution over time
                        cursor.execute(f"""
                            SELECT 
                                DATE({date_col}) as day,
                                COUNT(*) as count
                            FROM {schema.schema_name}.{table_name}
                            WHERE {date_col} >= CURRENT_DATE - INTERVAL '{request.time_range_days} days'
                            GROUP BY DATE({date_col})
                            ORDER BY day DESC
                            LIMIT 30
                        """)
                        
                        rows = cursor.fetchall()
                        
                        if rows and len(rows) >= 7:
                            counts = [row[1] for row in rows]
                            avg_daily = sum(counts) / len(counts)
                            recent_avg = sum(counts[:3]) / min(3, len(counts))
                            older_avg = sum(counts[-3:]) / min(3, len(counts))
                            
                            # Detect trend
                            if recent_avg > older_avg * 1.2:
                                change_pct = ((recent_avg - older_avg) / older_avg) * 100
                                insight_id = self._generate_insight_id(f"trend-up-{table_name}")
                                
                                insights.append(Insight(
                                    id=insight_id,
                                    type=InsightType.TREND,
                                    severity=InsightSeverity.MEDIUM,
                                    title=f"Increasing activity in {table_name}",
                                    description=f"Recent activity in {table_name} is {change_pct:.0f}% higher than earlier period",
                                    facts=[
                                        f"Recent average: {recent_avg:.0f} records/day",
                                        f"Earlier average: {older_avg:.0f} records/day",
                                        f"Trend observed over {len(rows)} days"
                                    ],
                                    metric_value=recent_avg,
                                    metric_label="Recent Daily Average",
                                    change_percent=change_pct,
                                    confidence=0.85
                                ))
                            
                            elif recent_avg < older_avg * 0.8:
                                change_pct = ((recent_avg - older_avg) / older_avg) * 100
                                insight_id = self._generate_insight_id(f"trend-down-{table_name}")
                                
                                insights.append(Insight(
                                    id=insight_id,
                                    type=InsightType.TREND,
                                    severity=InsightSeverity.MEDIUM,
                                    title=f"Decreasing activity in {table_name}",
                                    description=f"Recent activity in {table_name} is {abs(change_pct):.0f}% lower than earlier period",
                                    facts=[
                                        f"Recent average: {recent_avg:.0f} records/day",
                                        f"Earlier average: {older_avg:.0f} records/day",
                                        f"Trend observed over {len(rows)} days"
                                    ],
                                    metric_value=recent_avg,
                                    metric_label="Recent Daily Average",
                                    change_percent=change_pct,
                                    confidence=0.85
                                ))
        
        except Exception as e:
            logger.error(f"Error generating trend insights: {e}")
        finally:
            if conn:
                self.manager.release_connection(request.connection_id, conn)
        
        return insights
    
    def _generate_anomaly_insights(self, request: InsightsRequest, schema) -> List[Insight]:
        """Detect anomalies in numeric data."""
        insights = []
        conn = None
        
        try:
            conn = self.manager.get_connection(request.connection_id)
            
            # Look for numeric columns in tables
            for table_name, table in schema.tables.items():
                numeric_cols = [
                    col.name for col in table.columns
                    if col.data_type.lower() in ['integer', 'bigint', 'numeric', 'decimal', 'real', 'double precision']
                ]
                
                if numeric_cols and table.row_count and table.row_count > 50:
                    # Analyze first numeric column
                    col_name = numeric_cols[0]
                    
                    with conn.cursor() as cursor:
                        cursor.execute(f"""
                            SELECT {col_name}
                            FROM {schema.schema_name}.{table_name}
                            WHERE {col_name} IS NOT NULL
                            LIMIT 1000
                        """)
                        
                        values = [float(row[0]) for row in cursor.fetchall()]
                        
                        if len(values) >= 30:
                            # Detect anomalies
                            result = self.anomaly_detector.detect_anomalies(
                                values=values,
                                method=AnomalyMethod.Z_SCORE,
                                threshold=3.0
                            )
                            
                            if result.anomalies and result.anomaly_rate > 0.05:
                                insight_id = self._generate_insight_id(f"anomaly-{table_name}-{col_name}")
                                
                                avg_value = sum(values) / len(values)
                                anomaly_values = [a.value for a in result.anomalies[:3]]
                                
                                insights.append(Insight(
                                    id=insight_id,
                                    type=InsightType.ANOMALY,
                                    severity=InsightSeverity.HIGH if result.anomaly_rate > 0.1 else InsightSeverity.MEDIUM,
                                    title=f"Anomalies detected in {table_name}.{col_name}",
                                    description=f"Found {len(result.anomalies)} anomalous values in {col_name}",
                                    facts=[
                                        f"Detected {len(result.anomalies)} anomalies out of {len(values)} values",
                                        f"Anomaly rate: {result.anomaly_rate*100:.1f}%",
                                        f"Average value: {avg_value:.2f}",
                                        f"Sample anomalies: {', '.join(f'{v:.2f}' for v in anomaly_values)}"
                                    ],
                                    metric_value=result.anomaly_rate * 100,
                                    metric_label="Anomaly Rate %",
                                    confidence=0.8,
                                    data={"method": result.method.value}
                                ))
        
        except Exception as e:
            logger.error(f"Error generating anomaly insights: {e}")
        finally:
            if conn:
                self.manager.release_connection(request.connection_id, conn)
        
        return insights
    
    def _generate_comparison_insights(self, request: InsightsRequest, schema) -> List[Insight]:
        """Generate comparison insights between entities."""
        insights = []
        conn = None
        
        try:
            conn = self.manager.get_connection(request.connection_id)
            
            # Look for tables with name/category columns and numeric columns
            for table_name, table in schema.tables.items():
                name_cols = [col.name for col in table.columns if 'name' in col.name.lower()]
                numeric_cols = [
                    col.name for col in table.columns
                    if col.data_type.lower() in ['integer', 'bigint', 'numeric', 'decimal']
                ]
                
                if name_cols and numeric_cols and table.row_count and table.row_count > 5:
                    name_col = name_cols[0]
                    value_col = numeric_cols[0]
                    
                    with conn.cursor() as cursor:
                        cursor.execute(f"""
                            SELECT {name_col}, {value_col}
                            FROM {schema.schema_name}.{table_name}
                            WHERE {value_col} IS NOT NULL
                            ORDER BY {value_col} DESC
                            LIMIT 10
                        """)
                        
                        rows = cursor.fetchall()
                        
                        if rows and len(rows) >= 3:
                            top_name, top_value = rows[0][0], float(rows[0][1])
                            bottom_name, bottom_value = rows[-1][0], float(rows[-1][1])
                            
                            if top_value > bottom_value:
                                ratio = top_value / bottom_value if bottom_value > 0 else 0
                                insight_id = self._generate_insight_id(f"compare-{table_name}")
                                
                                insights.append(Insight(
                                    id=insight_id,
                                    type=InsightType.COMPARISON,
                                    severity=InsightSeverity.INFO,
                                    title=f"Top performer in {table_name}",
                                    description=f"{top_name} leads in {value_col}",
                                    facts=[
                                        f"Top: {top_name} with {top_value:,.0f}",
                                        f"Analyzed {len(rows)} entities",
                                        f"Spread: {ratio:.1f}x difference between top and bottom"
                                    ],
                                    metric_value=top_value,
                                    metric_label=value_col,
                                    confidence=0.9
                                ))
        
        except Exception as e:
            logger.error(f"Error generating comparison insights: {e}")
        finally:
            if conn:
                self.manager.release_connection(request.connection_id, conn)
        
        return insights
    
    def _generate_quality_insights(self, request: InsightsRequest, schema) -> List[Insight]:
        """Generate data quality insights."""
        insights = []
        conn = None
        
        try:
            conn = self.manager.get_connection(request.connection_id)
            
            for table_name, table in schema.tables.items():
                if not table.row_count or table.row_count == 0:
                    continue
                
                # Check for null values in columns
                for column in table.columns:
                    with conn.cursor() as cursor:
                        cursor.execute(f"""
                            SELECT 
                                COUNT(*) as total,
                                COUNT({column.name}) as non_null
                            FROM {schema.schema_name}.{table_name}
                        """)
                        
                        row = cursor.fetchone()
                        if row:
                            total, non_null = row
                            null_count = total - non_null
                            null_rate = (null_count / total) * 100 if total > 0 else 0
                            
                            if null_rate > 20:
                                insight_id = self._generate_insight_id(f"quality-nulls-{table_name}-{column.name}")
                                
                                insights.append(Insight(
                                    id=insight_id,
                                    type=InsightType.QUALITY,
                                    severity=InsightSeverity.HIGH if null_rate > 50 else InsightSeverity.MEDIUM,
                                    title=f"High null rate in {table_name}.{column.name}",
                                    description=f"{null_rate:.0f}% of values are null in {column.name}",
                                    facts=[
                                        f"Null values: {null_count:,} out of {total:,}",
                                        f"Null rate: {null_rate:.1f}%",
                                        "High null rates may indicate data collection issues"
                                    ],
                                    metric_value=null_rate,
                                    metric_label="Null Rate %",
                                    confidence=0.95
                                ))
        
        except Exception as e:
            logger.error(f"Error generating quality insights: {e}")
        finally:
            if conn:
                self.manager.release_connection(request.connection_id, conn)
        
        return insights
    
    def _generate_usage_insights(self, request: InsightsRequest, schema) -> List[Insight]:
        """Generate usage pattern insights."""
        insights = []
        
        # Schema-level insights
        insight_id = self._generate_insight_id(f"usage-schema-{request.connection_id}")
        
        table_count = len(schema.tables)
        total_columns = sum(len(t.columns) for t in schema.tables.values())
        total_rows = sum(t.row_count or 0 for t in schema.tables.values())
        
        insights.append(Insight(
            id=insight_id,
            type=InsightType.USAGE,
            severity=InsightSeverity.INFO,
            title=f"Database overview: {schema.schema_name}",
            description=f"Database contains {table_count} tables with {total_rows:,} total rows",
            facts=[
                f"Total tables: {table_count}",
                f"Total columns: {total_columns}",
                f"Total rows: {total_rows:,}",
                f"Relationships: {len(schema.relationships)}"
            ],
            metric_value=float(total_rows),
            metric_label="Total Rows",
            confidence=1.0
        ))
        
        return insights
    
    def _filter_by_role(self, insights: List[Insight], user_role) -> List[Insight]:
        """Filter and prioritize insights based on user role/persona."""
        from src.insights.models import UserRole
        
        # Role-based insight preferences
        role_preferences = {
            UserRole.EXECUTIVE: {
                'types': [InsightType.TREND, InsightType.FORECAST, InsightType.PERFORMANCE, InsightType.COMPARISON],
                'min_severity': InsightSeverity.MEDIUM,
                'boost_types': [InsightType.FORECAST, InsightType.TREND]
            },
            UserRole.TRADER: {
                'types': [InsightType.ANOMALY, InsightType.TREND, InsightType.PATTERN, InsightType.FORECAST],
                'min_severity': InsightSeverity.INFO,
                'boost_types': [InsightType.ANOMALY, InsightType.FORECAST],
                'time_focus': 'short'  # Focus on recent, real-time patterns
            },
            UserRole.INVESTOR: {
                'types': [InsightType.TREND, InsightType.FORECAST, InsightType.ATTRIBUTION, InsightType.COMPARISON],
                'min_severity': InsightSeverity.LOW,
                'boost_types': [InsightType.TREND, InsightType.FORECAST],
                'time_focus': 'long'  # Focus on long-term trends
            },
            UserRole.ANALYST: {
                'types': list(InsightType),  # All types
                'min_severity': InsightSeverity.INFO,
                'boost_types': [InsightType.QUALITY, InsightType.ATTRIBUTION, InsightType.PATTERN]
            },
            UserRole.MANAGER: {
                'types': [InsightType.PERFORMANCE, InsightType.COMPARISON, InsightType.TREND, InsightType.ATTRIBUTION],
                'min_severity': InsightSeverity.LOW,
                'boost_types': [InsightType.PERFORMANCE, InsightType.COMPARISON]
            },
            UserRole.SALES: {
                'types': [InsightType.TREND, InsightType.COMPARISON, InsightType.PERFORMANCE, InsightType.FORECAST],
                'min_severity': InsightSeverity.LOW,
                'boost_types': [InsightType.COMPARISON, InsightType.PERFORMANCE]
            },
            UserRole.OPERATIONS: {
                'types': [InsightType.QUALITY, InsightType.PATTERN, InsightType.ANOMALY, InsightType.PERFORMANCE],
                'min_severity': InsightSeverity.LOW,
                'boost_types': [InsightType.QUALITY, InsightType.ANOMALY]
            },
            UserRole.FINANCE: {
                'types': [InsightType.FORECAST, InsightType.TREND, InsightType.ATTRIBUTION, InsightType.COMPARISON],
                'min_severity': InsightSeverity.MEDIUM,
                'boost_types': [InsightType.FORECAST, InsightType.ATTRIBUTION]
            },
            UserRole.AGENT: {
                'types': [InsightType.ANOMALY, InsightType.PATTERN, InsightType.QUALITY],
                'min_severity': InsightSeverity.INFO,
                'boost_types': [InsightType.ANOMALY]
            }
        }
        
        prefs = role_preferences.get(user_role)
        if not prefs:
            return insights  # No filtering if role not recognized
        
        # Filter by preferred types
        filtered = [i for i in insights if i.type in prefs['types']]
        
        # Boost impact scores for preferred types
        for insight in filtered:
            if insight.type in prefs.get('boost_types', []):
                if insight.impact_score:
                    insight.impact_score = min(1.0, insight.impact_score * 1.3)
        
        return filtered
    
    def _generate_narrative(self, insight: Insight, user_role=None) -> str:
        """Generate LLM narrative for an insight, tailored to user role."""
        from src.insights.models import UserRole
        
        # Role-specific context
        role_context = ""
        if user_role:
            role_contexts = {
                UserRole.EXECUTIVE: "Focus on strategic implications and business impact. Use executive-level language.",
                UserRole.TRADER: "Focus on actionable, time-sensitive information. Emphasize speed and risk.",
                UserRole.INVESTOR: "Focus on long-term value, growth potential, and risk assessment.",
                UserRole.ANALYST: "Provide detailed, technical analysis with data quality considerations.",
                UserRole.MANAGER: "Focus on team performance, operational metrics, and actionable next steps.",
                UserRole.SALES: "Focus on revenue impact, customer insights, and conversion opportunities.",
                UserRole.OPERATIONS: "Focus on efficiency, bottlenecks, and process improvements.",
                UserRole.FINANCE: "Focus on cost implications, budget impact, and financial forecasts.",
                UserRole.AGENT: "Focus on immediate, actionable tasks and clear next steps."
            }
            role_context = role_contexts.get(user_role, "")
        
        try:
            prompt = f"""Generate a brief, clear explanation for this data insight.
Be concise (2-3 sentences), factual, and actionable.

Insight Type: {insight.type.value}
Title: {insight.title}
Description: {insight.description}
Facts: {', '.join(insight.facts)}

{"Audience: " + role_context if role_context else ""}

Generate a narrative that explains what this means and why it matters."""

            response = self.llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a data analyst explaining insights clearly and concisely."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=150
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            logger.error(f"Error generating narrative: {e}")
            return insight.description
    
    def _generate_actions(self, insight: Insight, user_role=None) -> List[str]:
        """Generate suggested actions for an insight, tailored to user role."""
        from src.insights.models import UserRole
        
        # Base actions by insight type
        base_actions = {
            InsightType.ANOMALY: [
                "Investigate the anomalous values for data entry errors",
                "Review business events that may explain unusual values",
                "Consider adding validation rules"
            ],
            InsightType.TREND: [
                "Monitor the trend for continued changes",
                "Analyze factors driving the trend",
                "Plan capacity if trend continues"
            ],
            InsightType.QUALITY: [
                "Review data collection processes",
                "Implement validation at data entry",
                "Consider required field constraints"
            ],
            InsightType.PATTERN: [
                "Optimize queries for large tables",
                "Consider indexing frequently queried columns",
                "Review table design for performance"
            ],
            InsightType.COMPARISON: [
                "Analyze what makes top performers successful",
                "Share best practices across entities",
                "Set benchmarks based on leaders"
            ],
            InsightType.FORECAST: [
                "Plan resources based on predictions",
                "Monitor actual vs forecast accuracy",
                "Adjust strategies for anticipated changes"
            ],
            InsightType.ATTRIBUTION: [
                "Focus on high-impact drivers",
                "Test hypotheses about causal relationships",
                "Optimize levers with strongest influence"
            ]
        }
        
        actions = base_actions.get(insight.type, ["Review and monitor this insight"])
        
        # Role-specific action modifications
        if user_role == UserRole.TRADER:
            actions = [a.replace("Monitor", "Track real-time").replace("Plan", "Execute quickly") for a in actions]
        elif user_role == UserRole.EXECUTIVE:
            actions = [a.replace("Investigate", "Commission analysis on").replace("Review", "Evaluate strategic impact of") for a in actions]
        elif user_role == UserRole.AGENT:
            actions = [a.replace("Analyze", "Check").replace("Consider", "Document") for a in actions]
        
        return actions[:3]  # Limit to top 3 actions
    
    def _generate_summary(self, connection, insight_cards: List[InsightCard]) -> str:
        """Generate overall analysis summary."""
        if not insight_cards:
            return f"No significant insights found for {connection.name}."
        
        severity_counts = {}
        type_counts = {}
        
        for card in insight_cards:
            severity_counts[card.insight.severity.value] = severity_counts.get(card.insight.severity.value, 0) + 1
            type_counts[card.insight.type.value] = type_counts.get(card.insight.type.value, 0) + 1
        
        summary_parts = [
            f"Generated {len(insight_cards)} insights for {connection.name}."
        ]
        
        if severity_counts.get('critical', 0) > 0 or severity_counts.get('high', 0) > 0:
            summary_parts.append(f"Found {severity_counts.get('critical', 0) + severity_counts.get('high', 0)} high-priority items requiring attention.")
        
        top_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:2]
        if top_types:
            type_str = ', '.join(f"{count} {type_name}" for type_name, count in top_types)
            summary_parts.append(f"Key findings: {type_str}.")
        
        return " ".join(summary_parts)
    
    def _generate_insight_id(self, base: str) -> str:
        """Generate unique insight ID."""
        timestamp = datetime.utcnow().isoformat()
        content = f"{base}-{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _generate_forecast_insights(self, request: InsightsRequest, schema) -> List[Insight]:
        """Generate forecast insights using time series analysis."""
        insights = []
        conn = None
        
        try:
            conn = self.manager.get_connection(request.connection_id)
            
            # Look for tables with date/timestamp columns and numeric metrics
            for table_name, table in schema.tables.items():
                date_columns = [
                    col.name for col in table.columns 
                    if 'date' in col.name.lower() or 'time' in col.name.lower()
                ]
                
                numeric_cols = [
                    col.name for col in table.columns
                    if col.data_type.lower() in ['integer', 'bigint', 'numeric', 'decimal']
                ]
                
                if date_columns and numeric_cols and table.row_count and table.row_count > 20:
                    date_col = date_columns[0]
                    value_col = numeric_cols[0]
                    
                    with conn.cursor() as cursor:
                        # Get time series data
                        cursor.execute(f"""
                            SELECT DATE({date_col}) as day, SUM({value_col}) as total
                            FROM {schema.schema_name}.{table_name}
                            WHERE {date_col} >= CURRENT_DATE - INTERVAL '30 days'
                            GROUP BY DATE({date_col})
                            ORDER BY day
                            LIMIT 30
                        """)
                        
                        rows = cursor.fetchall()
                        
                        if rows and len(rows) >= 7:
                            values = [float(row[1]) for row in rows if row[1] is not None]
                            
                            if len(values) >= 7:
                                # Generate forecast
                                forecast_result = self.forecaster.forecast(
                                    values=values,
                                    periods=7,
                                    method=ForecastMethod.LINEAR
                                )
                                
                                # Create insight
                                avg_current = sum(values) / len(values)
                                avg_forecast = sum(f.value for f in forecast_result.forecasts) / len(forecast_result.forecasts)
                                change_pct = ((avg_forecast - avg_current) / avg_current) * 100 if avg_current > 0 else 0
                                
                                insight_id = self._generate_insight_id(f"forecast-{table_name}-{value_col}")
                                
                                facts = [
                                    f"Historical average: {avg_current:.2f}",
                                    f"Forecasted average (next 7 days): {avg_forecast:.2f}",
                                    f"Trend direction: {forecast_result.trend_direction}",
                                    f"Trend strength: {forecast_result.trend_strength:.0%}"
                                ]
                                
                                if forecast_result.trend_direction == "up":
                                    title = f"Forecasted increase in {table_name}.{value_col}"
                                    severity = InsightSeverity.MEDIUM
                                elif forecast_result.trend_direction == "down":
                                    title = f"Forecasted decrease in {table_name}.{value_col}"
                                    severity = InsightSeverity.MEDIUM
                                else:
                                    title = f"Stable forecast for {table_name}.{value_col}"
                                    severity = InsightSeverity.INFO
                                
                                insights.append(Insight(
                                    id=insight_id,
                                    type=InsightType.FORECAST,
                                    severity=severity,
                                    title=title,
                                    description=f"7-day forecast shows {forecast_result.trend_direction} trend",
                                    facts=facts,
                                    metric_value=avg_forecast,
                                    metric_label=f"Forecast {value_col}",
                                    change_percent=change_pct,
                                    confidence=0.75 * forecast_result.trend_strength,
                                    forecast_data={
                                        "method": forecast_result.method.value,
                                        "predictions": [
                                            {"period": f.timestamp, "value": f.value, "confidence": f.confidence}
                                            for f in forecast_result.forecasts
                                        ]
                                    }
                                ))
                                break  # Only one forecast insight per scan
        
        except Exception as e:
            logger.error(f"Error generating forecast insights: {e}")
        finally:
            if conn:
                self.manager.release_connection(request.connection_id, conn)
        
        return insights
    
    def _generate_attribution_insights(self, request: InsightsRequest, schema) -> List[Insight]:
        """Generate attribution insights - what drives metrics."""
        insights = []
        conn = None
        
        try:
            conn = self.manager.get_connection(request.connection_id)
            
            # Look for tables with multiple numeric columns
            for table_name, table in schema.tables.items():
                numeric_cols = [
                    col.name for col in table.columns
                    if col.data_type.lower() in ['integer', 'bigint', 'numeric', 'decimal']
                ]
                
                if len(numeric_cols) >= 3 and table.row_count and table.row_count > 10:
                    target_col = numeric_cols[0]
                    factor_cols = numeric_cols[1:4]
                    
                    with conn.cursor() as cursor:
                        cols_str = ', '.join([target_col] + factor_cols)
                        cursor.execute(f"""
                            SELECT {cols_str}
                            FROM {schema.schema_name}.{table_name}
                            WHERE {target_col} IS NOT NULL
                            LIMIT 100
                        """)
                        
                        rows = cursor.fetchall()
                        
                        if rows and len(rows) >= 10:
                            target_values = [float(row[0]) for row in rows if row[0] is not None]
                            factor_values = {}
                            
                            for idx, factor_col in enumerate(factor_cols, start=1):
                                values = [float(row[idx]) for row in rows if row[idx] is not None]
                                if len(values) == len(target_values):
                                    factor_values[factor_col] = values
                            
                            if len(factor_values) >= 2:
                                attribution = self.attribution_analyzer.analyze_drivers(
                                    target_values=target_values,
                                    factor_values=factor_values,
                                    target_name=target_col
                                )
                                
                                if attribution.factors and attribution.top_driver:
                                    insight_id = self._generate_insight_id(f"attribution-{table_name}-{target_col}")
                                    
                                    facts = [
                                        f"Analyzing what drives {target_col}",
                                        f"Top driver: {attribution.top_driver}",
                                        f"Explained variance: {attribution.explained_variance:.0%}"
                                    ]
                                    
                                    for factor in attribution.factors[:3]:
                                        direction = "positively" if factor.direction == "positive" else "negatively" if factor.direction == "negative" else "weakly"
                                        facts.append(f"{factor.factor_name}: {direction} correlated ({factor.correlation:.2f})")
                                    
                                    insights.append(Insight(
                                        id=insight_id,
                                        type=InsightType.ATTRIBUTION,
                                        severity=InsightSeverity.MEDIUM,
                                        title=f"Key drivers of {target_col} in {table_name}",
                                        description=f"{attribution.top_driver} is the strongest driver of {target_col}",
                                        facts=facts,
                                        metric_value=attribution.explained_variance * 100,
                                        metric_label="Explained Variance %",
                                        confidence=0.7 + (attribution.explained_variance * 0.2),
                                        attribution_data={
                                            "target": attribution.target_metric,
                                            "top_driver": attribution.top_driver,
                                            "factors": [
                                                {
                                                    "name": f.factor_name,
                                                    "correlation": f.correlation,
                                                    "importance": f.importance,
                                                    "direction": f.direction
                                                }
                                                for f in attribution.factors
                                            ]
                                        }
                                    ))
                                    break
        
        except Exception as e:
            logger.error(f"Error generating attribution insights: {e}")
        finally:
            if conn:
                self.manager.release_connection(request.connection_id, conn)
        
        return insights


# Singleton
_insight_generator = None

def get_insight_generator() -> InsightGenerator:
    """Get singleton InsightGenerator instance."""
    global _insight_generator
    if _insight_generator is None:
        _insight_generator = InsightGenerator()
    return _insight_generator
