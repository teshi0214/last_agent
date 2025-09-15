# Google Scholar Agent

## Overview

The Google Scholar Agent is designed to assist researchers by providing relevant academic papers, author metadata, and news related to their research interests. This agent serves as the foundational component for the larger GrantAI project, offering a practical example for developing sophisticated AI agents.

## User Story

As a researcher, I want an agent that can:

* Find papers relevant to my interests.

* Retrieve author metadata (name, affiliations, interests, profile URL, articles published) upon request, specifically by Author ID.

* Find news related to my research to support my ongoing work.

## Background

This project is a starter for developing agents within the GrantAI ecosystem. It provides hands-on experience with agent development principles and establishes a model for future agents integrated into GrantAI.

## Key Features / Subtask Breakdown

The agent will be equipped with the following capabilities:

* **Author Metadata Retrieval:** An Agent Tool to retrieve comprehensive author metadata, including name, affiliations, interests, profile URL, and a list of published articles.

* **Research Paper Search:** An Agent Tool to search and retrieve research papers from Google Scholar based on user-defined keywords or interests.

* **Research News Search:** An Agent Tool to search Google News for articles and updates relevant to specific research topics.

* **Generic Google Search Sub-Agent:** A Sub-Agent capable of performing general web searches to supplement the specialized tools.

## References

* [Mark's Google Scholar Agent Design Doc](https://docs.google.com/document/d/1jmyIj4ruiHVlS5ZWbmSXbfLY60Jn2kq3LPQ7oArm5XE/edit?tab=t.0#heading=h.2xajk66oyqmg)

* [SerpAPI - Google Scholar API Documentation](https://serpapi.com/google-scholar-api)

## Development and Testing

### Test Plan

Agent Evaluation test cases will be implemented and executed using the Agent Development Kit (ADK) to ensure functionality and reliability.

### Acceptance Criteria

1. All implemented Agent Tools perform as expected according to their specifications.

2. All Agent Evaluation Test Cases pass successfully.

## Review

(Link to review document/platform will be placed here)

### Project Structure

The core functionality involves `prompt.py` for agent interaction and direct calls to the Google Scholar API. Author information retrieval will leverage the Author ID