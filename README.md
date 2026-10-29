# RoadSense Web

**AI-powered pothole mapping and road intelligence platform.**

RoadSense Web visualizes pothole detections collected by the RoadSense Android app, organizes them into geographic records, and uses AI-assisted web research to discover related public road-work and tender information.

## Features

- **Interactive map:** Explore pothole locations, markers, zoom levels, and date-based filters.
- **Detection ledger:** Search and browse recorded potholes.
- **Pothole details:** View coordinates, timestamps, observation counts, confidence, and geographic metadata.
- **Road identification:** Resolve road names and administrative information using geographic data.
- **Contract research:** Search for potentially related government projects and tender records.
- **Local AI research:** Use Ollama and a lightweight Qwen model to analyze retrieved information.
- **Self-hosted web search:** Use SearXNG without requiring a paid Google or Brave Search API.
- **Evidence and provenance:** Present source links, evidence excerpts, and research status.
- **Dark mode:** Switch between light and dark themes.

## Technology Stack

| Component | Technology |
|---|---|
| Frontend build tooling | Vite |
| Interactive mapping | Leaflet |
| Map tiles | Configured map provider, with OpenStreetMap-derived geographic data where applicable |
| Backend | Python API service |
| Data storage | Configured backend database |
| Object detection | YOLO model exported to ONNX, used by the Android app |
| Local LLM runtime | Ollama |
| Language model | Qwen 0.6B model, subject to deployed configuration |
| Web search | SearXNG |
| Deployment | Docker-based services and self-hosted infrastructure |

Refer to `package.json`, the backend dependency files, model configuration, and Docker Compose files for exact package versions and runtime dependencies.

## Architecture

```text
RoadSense Android App
        |
        | Pothole observations + GPS metadata
        v
RoadSense Backend API
        |
        +------> Database
        |           |
        |           v
        |      RoadSense Web
        |
        +------> Research Service
                     |
                     v
                  SearXNG
                     |
                     v
                Public Web
                     |
                     v
                   Ollama
                     |
                     v
             Evidence extraction
                     |
                     v
              Research results
