# StoryMecha

Intelligent story validator that detects physics impossibilities, visualizes concepts, and answers questions with grounded AI reasoning.

## Overview

StoryMecha is an AI-powered narrative analysis system that combines symbolic reasoning, pattern-based physics validation, and neural language models to provide comprehensive story analysis. The system automatically detects physics violations across 10 fundamental physics categories, constructs interactive knowledge graphs from narrative concepts, and answers user questions with hallucination-prevention mechanisms.

## Key Features

- **Physics Violation Detection**: Automatically detects violations of 10 fundamental physics categories with 29+ pattern-based rules achieving 100% detection rate on test cases
- **Knowledge Graph Construction**: Builds interactive knowledge graphs from story concepts using ConceptNet API integration with Cytoscape.js visualization
- **Grounded Question Answering**: Answers questions about stories using TinyLlama-1.1B LLM with multi-layer hallucination prevention
- **Real-Time Analysis**: Processes typical stories in under 3 seconds with concurrent API calls and intelligent caching
- **Multi-Session Support**: Manage multiple story analysis sessions with persistent storage
- **Context-Aware Validation**: 50-character context extraction around detected violations for accurate human review

## Physics Validation Categories

The system validates stories against the following physics categories:

1. **Gravity Violations** - Upward motion without force, terrain movement, reversed/selective gravity
2. **Energy Conservation** - Energy from nowhere, perpetual motion, self-sustaining systems
3. **Mass Conservation** - Spontaneous disappearance, duplication, partial vanishing
4. **Thermodynamics** - Heat flowing backward, instant temperature changes, temperature paradoxes
5. **Relativity** - Faster-than-light travel, time reversal, causality violations
6. **Newton's Laws** - Motion without applied force, no recoil, momentum violations
7. **Material Strength** - Impossible bending, infinite load support
8. **Biology & Survival** - Extended oxygen deprivation, indestructibility, immunity to massive forces
9. **Planetary Physics** - Orbits breaking, atmosphere detachment
10. **Quantum Physics** - Deterministic quantum behavior, macroscopic tunneling

## System Architecture

### Frontend Layer
- HTML5/CSS3/JavaScript single-page application
- Cytoscape.js for interactive graph visualization
- Real-time chat interface with multi-session support
- Web Speech API for voice input/output

### Backend Layer
- Flask REST API (Python 3.8+)
- TinyLlama-1.1B-Chat LLM for reasoning
- ConceptNet 5 API integration for knowledge relationships
- JSON-based session persistence

### Physics Validation Layer
- Pattern-based detection engine with regex matching
- 10 physics categories with 29+ violation patterns
- Context extraction and violation categorization
- HTML report generation with severity indicators

## Performance Metrics

| Metric | Value |
|--------|-------|
| Detection Rate | 100% (10/10 test cases) |
| False Positive Rate | <5% |
| Story Analysis Time (100 words) | ~2.7 seconds |
| Story Analysis Time (500 words) | ~3.5 seconds |
| Physics Validation Time | ~0.4 seconds |
| LLM Answer Generation (CPU) | 2-5 minutes |
| LLM Answer Generation (GPU) | 10-30 seconds |
| Knowledge Graph Size | 41 nodes, 35 relationships |
| Memory Usage (Model) | 2.2GB RAM |
| Max Concurrent Sessions | 10 stable |

## Requirements

### Hardware

**Minimum:**
- Processor: Intel Core i5 (4 cores, 2.5 GHz+) or AMD Ryzen 5
- RAM: 8 GB
- Storage: 5 GB free space
- Network: 5 Mbps broadband

**Recommended:**
- Processor: Intel Core i7/i9 or AMD Ryzen 7/9 (8+ cores)
- RAM: 16 GB
- Storage: 10 GB SSD
- GPU: NVIDIA with CUDA support (GTX 1060+ or better) for 10-20x speedup

### Operating Systems

- Windows 10/11 (64-bit)
- macOS 10.14+ (all versions including M1/M2/M3)
- Linux: Ubuntu 20.04+, Debian 11+, Fedora 35+, CentOS 8+

### Software Stack

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.8-3.11 | Runtime environment |
| Flask | 2.3.2+ | Web framework |
| PyTorch | 2.0.1+ | Deep learning framework |
| Transformers | 4.30.2+ | LLM support |
| TinyLlama | 1.1B | Language model |
| Requests | 2.31.0+ | HTTP library |
| Cytoscape.js | 3.23+ | Graph visualization |

## Installation

### Quick Setup (5 minutes)

1. **Verify Python installation:**
   ```bash
   python --version  # Should show 3.8-3.11
   ```

2. **Clone repository:**
   ```bash
   git clone <repository-url>
   cd storymecha
   ```

3. **Create virtual environment:**
   ```bash
   python -m venv venv
   On Windows: venv\Scripts\activate
   On Others: source venv/bin/activate  
   ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Download TinyLlama model (one-time, ~2.2GB):**
   ```bash
   python down.py
   ```

6. **Start the server:**
   ```bash
   python server_with_physics.py
   ```

7. **Open in browser:**
   ```
   http://localhost:5000
   ```

### Dependencies

All required packages are listed in `requirements.txt`:

```
flask==2.3.2
flask-cors==4.0.0
requests==2.31.0
transformers==4.30.2
torch==2.0.1
accelerate==0.20.3
sentencepiece==0.1.99
protobuf==4.23.3
```

## Project Structure

```
storymecha/
├── server_with_physics.py       # Main server with physics validation
├── physics_validator.py          # Physics detection module
├── server.py                     # Original server (no physics)
├── llm_reasoner.py              # LLM inference engine
├── context_builder.py           # Prompt construction
├── graph_queries.py             # Graph utilities
├── down.py                      # Model downloader
├── index.html                   # Frontend UI
├── requirements.txt             # Python dependencies
├── stories.json                 # Session storage
├── conceptnet_cache.json        # API cache
├── README.md                    # This file
└── venv/                        # Virtual environment
```

## Usage

### Basic Workflow

1. **Create New Session**: Click "New Story" to start analysis
2. **Enter Story**: Paste or type your story text
3. **View Physics Validation**: Violations detected and displayed in ~0.4 seconds
4. **Explore Knowledge Graph**: Interactive visualization in dedicated tab
5. **Ask Questions**: Input questions to get LLM-powered answers grounded in the story
6. **Manage Sessions**: Rename or delete sessions from sidebar

### Example Test Story

**Story with Physics Violations:**
```
A brave knight flew upward without wings. He grabbed his sword that appeared 
from nowhere and defeated the dragon that vanished without a trace.
```

Expected Results:
- Gravity violation: "flew upward"
- Energy violation: "appeared from nowhere"
- Mass violation: "vanished without a trace"

**Normal Story (No Violations):**
```
A brave knight named Sir Arthur lived in a grand castle. A fierce dragon 
attacked the nearby village. Sir Arthur rode his horse to fight and defeated 
the dragon, saving the village.
```

Expected Results:
- No physics violations detected
- 7 concepts extracted
- 41-node knowledge graph
- Accurate question answering

## API Endpoints

### Session Management

```
GET /sessions
  Returns list of all story sessions

POST /sessions
  Creates new session

POST /sessions/{id}
  Updates session (e.g., rename)

DELETE /sessions/{id}
  Deletes session
```

### Story Analysis

```
POST /sessions/{id}/story
  Body: {"story": "..."}
  Returns: Analysis results + physics validation
  Time: ~2.7 seconds
```

### Question Answering

```
POST /sessions/{id}/question
  Body: {"question": "..."}
  Returns: LLM answer with grounding
  Time: 2-5 min (CPU) / 10-30s (GPU)
```

## Configuration

### Server Settings

Edit `server_with_physics.py`:
```python
PORT = 5000                        # Server port
DEBUG = False                      # Debug mode
CONCEPT_LIMIT = 7                 # Max concepts per story
CONCEPTNET_RELATIONS = 5           # Relations per concept
GRAPH_DEPTH = 2                    # Relationship depth
```

### Physics Validation Settings

Edit `physics_validator.py`:
```python
CONTEXT_CHARS = 50                 # Context window size
PATTERN_TIMEOUT = 5                # Regex timeout (seconds)
```

### LLM Settings

Edit `llm_reasoner.py`:
```python
MODEL_NAME = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
MAX_TOKENS_ANALYTICAL = 300
MAX_TOKENS_CREATIVE = 400
TEMPERATURE = 0.7
```

## Performance Optimization

### CPU Optimization
- Multi-threaded ConceptNet API calls (5 concurrent workers)
- Aggressive caching of ConceptNet responses
- Question cache with 80-90% hit rate
- Regex timeout protection (5 seconds)

### GPU Optimization
- Verify GPU detection: `python -c "import torch; print(torch.cuda.is_available())"`
- Install CUDA 11.7+ for optimal performance
- TinyLlama requires ~2GB VRAM
- Achieves 10-30 second inference time vs 2-5 minutes on CPU

### Network Optimization
- Parallel API calls reduce ConceptNet fetch time by 5x
- Connection pooling for HTTP requests
- CDN delivery for frontend libraries

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 5000 in use | Change PORT in server.py or kill existing process |
| LLM takes 5+ minutes | Use GPU or wait / Use cached answers |
| Out of memory | Close other apps / Ensure 8+ GB RAM available |
| ConceptNet timeout | Check internet connection / Retry |
| Physics false positives | Manual review / Add negative lookaheads to patterns |
| Model download fails | Retry `python down.py` / Check internet connection |
| Blank browser page | Check server is running / Restart server |

## Limitations

- **Physics Validation**: Pattern-based approach may miss unusually phrased violations
- **Genre Understanding**: Cannot distinguish intentional fantasy from physics errors
- **LLM Model Size**: 1.1B parameters limits reasoning complexity
- **Language Support**: Currently English-only for ConceptNet integration
- **Context Window**: Limited to 2048 tokens for prompt construction
- **Scalability**: In-memory storage suitable for prototype only

## Future Enhancements

### Short-Term (1-3 months)
- Chemistry violation detection (30+ patterns)
- Expand physics patterns to 50+
- Multi-language support (Spanish, French, German)
- Genre detection (fantasy vs. realistic fiction)

### Medium-Term (3-6 months)
- Upgrade to Llama-2-7B for better reasoning
- Semantic understanding of violations
- PostgreSQL backend for production scalability
- User authentication and multi-user support
- Violation severity scoring

### Long-Term (6-12 months)
- Mobile app (iOS/Android)
- Educational curriculum integration
- Cloud deployment with load balancing
- Integration with writing platforms
- Custom physics rule builder

## Use Cases

**Education**: Teaching physics through story analysis, identifying misconceptions in student writing

**Content Moderation**: Validating scientific accuracy in children's stories, quality control for educational content

**Creative Writing**: Physics consistency checking for sci-fi authors, world-building validation tool

**Research**: Analyzing physics understanding in text, corpus studies of scientific misconceptions, AI reasoning benchmarks

## Testing

All 10 physics categories have been validated with 100% detection rate on test cases. Integration tests confirm:
- Story analysis pipeline: PASSED
- Physics validation: PASSED
- LLM grounding: PASSED
- Session persistence: PASSED
- Browser compatibility (Chrome, Firefox, Safari, Edge): PASSED

## Contributing

To extend the system:

1. **Add Physics Category**: Edit physics_validator.py, add patterns
2. **Upgrade LLM**: Change MODEL_NAME in llm_reasoner.py, run `python down.py`
3. **Add Language Support**: Create language-specific stopwords, update ConceptNet calls

## License

MIT License

## Acknowledgments

- ConceptNet team (MIT Media Lab)
- HuggingFace community for transformers library
- PyTorch team for deep learning framework
- Open-source contributors and community



**Status**: Local Development  
**Version**: 2.0 (Physics-Enhanced)  
**Last Updated**: November 2025
