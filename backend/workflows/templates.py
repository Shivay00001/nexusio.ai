"""
NexusAI — Pre-built workflow templates.
"""

TEMPLATES = {
    "research_pipeline": {
        "name": "Research Pipeline",
        "description": "Search the web, extract content, and generate a summary report.",
        "steps": {
            "search": {
                "name": "Web Search",
                "type": "tool",
                "config": {
                    "tool": "web_search",
                    "args": {"query": "{{topic}}", "max_results": "5"},
                    "output_variable": "search_results",
                },
                "depends_on": [],
            },
            "summarize": {
                "name": "Summarize Findings",
                "type": "ai_chat",
                "config": {
                    "prompt": "Based on the following search results, create a comprehensive summary report about '{{topic}}':\n\n{{search_results}}\n\nProvide key findings, insights, and a conclusion.",
                    "output_variable": "summary",
                },
                "depends_on": ["search"],
            },
        },
    },
    "content_generator": {
        "name": "Content Generator",
        "description": "Generate structured content: outline → draft → polished version.",
        "steps": {
            "outline": {
                "name": "Create Outline",
                "type": "ai_chat",
                "config": {
                    "prompt": "Create a detailed outline for content about: {{topic}}\n\nInclude sections, subsections, and key points to cover.",
                    "output_variable": "outline",
                },
                "depends_on": [],
            },
            "draft": {
                "name": "Write Draft",
                "type": "ai_chat",
                "config": {
                    "prompt": "Using this outline, write a complete first draft:\n\n{{outline}}\n\nMake it detailed, informative, and engaging.",
                    "output_variable": "draft",
                },
                "depends_on": ["outline"],
            },
            "polish": {
                "name": "Polish & Finalize",
                "type": "ai_chat",
                "config": {
                    "prompt": "Review and polish this draft. Fix any issues, improve clarity, and make it publication-ready:\n\n{{draft}}",
                    "output_variable": "final_content",
                },
                "depends_on": ["draft"],
            },
        },
    },
    "code_assistant": {
        "name": "Code Assistant Pipeline",
        "description": "Understand a task, plan implementation, write code, and test it.",
        "steps": {
            "analyze": {
                "name": "Analyze Requirements",
                "type": "ai_chat",
                "config": {
                    "prompt": "Analyze these coding requirements and break them down into specific tasks:\n\n{{task}}\n\nList the approach, technologies needed, and implementation steps.",
                    "output_variable": "analysis",
                },
                "depends_on": [],
            },
            "implement": {
                "name": "Write Code",
                "type": "ai_chat",
                "config": {
                    "prompt": "Based on this analysis, write the complete implementation code:\n\n{{analysis}}\n\nProvide well-commented, production-quality code.",
                    "output_variable": "code",
                },
                "depends_on": ["analyze"],
            },
            "test": {
                "name": "Generate Tests",
                "type": "ai_chat",
                "config": {
                    "prompt": "Write comprehensive test cases for this code:\n\n{{code}}\n\nInclude unit tests and edge cases.",
                    "output_variable": "tests",
                },
                "depends_on": ["implement"],
            },
        },
    },
    "data_processor": {
        "name": "Data Processor",
        "description": "Fetch data from a URL, analyze it, and generate insights.",
        "steps": {
            "fetch": {
                "name": "Fetch Data",
                "type": "tool",
                "config": {
                    "tool": "extract_url",
                    "args": {"url": "{{url}}"},
                    "output_variable": "raw_data",
                },
                "depends_on": [],
            },
            "analyze": {
                "name": "Analyze Data",
                "type": "ai_chat",
                "config": {
                    "prompt": "Analyze the following data and extract key insights, patterns, and statistics:\n\n{{raw_data}}",
                    "output_variable": "analysis",
                },
                "depends_on": ["fetch"],
            },
            "report": {
                "name": "Generate Report",
                "type": "ai_chat",
                "config": {
                    "prompt": "Create a professional report based on this analysis:\n\n{{analysis}}\n\nInclude an executive summary, key findings, and recommendations.",
                    "output_variable": "report",
                },
                "depends_on": ["analyze"],
            },
        },
    },
}
