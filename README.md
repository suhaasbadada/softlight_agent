# SoftLight Agent

A specialized web automation system for Notion that uses AI to generate and execute precise UI interaction sequences.

## Architecture

### Core Components

**Task Models** (`task_models.py`)
- Defines data structures for automation tasks and steps
- `Step`: Individual UI actions with selectors, descriptions, and values
- `TaskRequest`: API input with target app and user instruction
- `TaskResponse`: Structured output with execution results

**Task Service** (`task_service.py`)
- Orchestrates the complete automation workflow
- Coordinates between AI step generation and browser execution
- Returns normalized response with captured results

**Capture Service** (`capture_service.py`)
- Handles browser automation using Playwright with persistent sessions
- Implements intelligent element detection with multiple fallback strategies
- Manages Notion-specific authentication states and timeouts
- Provides step verification with screenshot capture
- Includes specialized logic for Notion UI patterns and workflows

**LLM Agent** (`llm_agent.py`)
- Generates precise UI interaction sequences using Groq's language models
- Contains embedded knowledge of Notion's UI structure and common workflows
- Translates natural language instructions into executable automation steps
- Ensures reliable step generation for complex Notion operations

**Page Analyzer** (`page_analyzer.py`)
- Performs real-time analysis of current page state
- Detects interactive elements and categorizes them by role
- Provides contextual information for AI step generation
- Identifies authentication states and workspace detection

## Key Features

**Notion-Specific Automation**
- Specialized element detection for Notion's complex UI
- Handles authentication flow and workspace detection
- Supports common operations: database creation, search, settings management
- Intelligent waiting for UI state transitions

**AI-Powered Step Generation**
- Converts natural language instructions into precise UI actions
- Uses contextual page analysis to inform step generation
- Implements fallback strategies for element location
- Maintains knowledge of Notion's UI patterns and workflows

**Robust Execution Engine**
- Multiple element location strategies (text, CSS, XPath, attributes)
- Comprehensive error handling and recovery
- Action verification with visual confirmation
- Persistent browser sessions maintaining login state

**API Interface**
- RESTful endpoints for task execution
- Structured request/response format
- Detailed step-by-step execution reporting
- Screenshot capture for verification and debugging

## Supported Notion Operations

- Database creation and management
- Search and navigation
- Settings and appearance configuration
- Page creation and content management
- Workspace navigation and organization

The system combines AI-driven planning with robust browser automation to handle Notion's dynamic interface, providing reliable automation for complex user workflows.
