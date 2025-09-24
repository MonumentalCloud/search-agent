# Chat GUI Documentation

## Overview

The Retrieval Agent includes a beautiful, interactive chat interface built with Streamlit that provides real-time streaming of the agent's thought process, citations, and performance metrics.

## Features

### 🎨 **Beautiful Interface**
- Modern, responsive design with custom CSS styling
- Color-coded messages (user vs agent)
- Professional Korean financial regulation theme

### 🧠 **Thought Process Visualization**
- **Real-time streaming** of agent reasoning
- **Performance metrics** with visual gauges
- **Query analysis** breakdown
- **Response time** tracking with performance indicators

### 📚 **Citation Management**
- **Source tracking** with document IDs
- **Section references** for precise citations
- **Validity periods** for time-sensitive information
- **Chunk-level** granularity

### 📊 **Analytics Dashboard**
- **Message statistics** (total, user queries, agent responses)
- **Performance charts** with Plotly visualizations
- **Response time gauges** with color-coded performance levels
- **System status** monitoring

### 🌐 **Multi-language Support**
- **Korean** and **English** language selection
- **Time hints** for temporal context
- **Sample queries** in Korean financial regulation domain

## Quick Start

### Option 1: Direct Launch
```bash
python chat.py
```

### Option 2: Via Startup Script
```bash
python start.py --chat-only
```

### Option 3: Via Makefile
```bash
make chat
```

### Option 4: Demo Mode
```bash
python demo.py --mode both    # Start API + Chat GUI
```

## Interface Components

### Main Chat Area
- **Message History**: Persistent conversation with user and agent messages
- **Input Field**: Text input with placeholder suggestions
- **Send Button**: Submit queries to the agent
- **Sample Queries**: Pre-loaded Korean financial regulation questions

### Sidebar Configuration
- **API Status**: Real-time connection status indicator
- **Language Selection**: Korean/English toggle
- **Time Hints**: Optional temporal context input
- **Sample Queries**: Quick access to common questions
- **Clear Chat**: Reset conversation history

### Analytics Panel
- **Performance Metrics**: Response time, message counts
- **Visual Charts**: Plotly-based performance gauges
- **System Information**: API URL, status, configuration

### Thinking Process Panel
- **Query Analysis**: Intent, entities, time context breakdown
- **Performance Indicators**: Fast/Moderate/Slow response classification
- **Result Preview**: Response length, citation count
- **Trace Details**: Debug information for troubleshooting

## Sample Queries

The interface includes pre-loaded sample queries for Korean financial regulations:

1. **전자금융거래법 시행령에서 규정하는 내용은 무엇인가요?**
   - "What are the regulations in the Electronic Financial Transactions Act?"

2. **ISA 계좌 이전하는 방법**
   - "How to transfer ISA account"

3. **장기주택마련저축 정의**
   - "Definition of long-term housing savings"

4. **출산 장려금 자격 요건**
   - "Eligibility requirements for childbirth incentives"

5. **금융감독규정 시행세칙**
   - "Financial supervision regulation implementation rules"

## Technical Details

### Dependencies
- **Streamlit**: Web interface framework
- **Plotly**: Interactive visualizations
- **Requests**: API communication
- **Custom CSS**: Professional styling

### API Integration
- **Health Checks**: Automatic API status monitoring
- **Query Streaming**: Real-time response processing
- **Trace Retrieval**: Debug information access
- **Error Handling**: Graceful failure management

### Performance Features
- **Response Time Tracking**: Millisecond precision
- **Performance Gauges**: Visual performance indicators
- **Caching**: Efficient data retrieval
- **Async Operations**: Non-blocking UI updates

## Configuration

### API Endpoint
Default: `http://localhost:8001`
- Configurable via environment variables
- Automatic health checking
- Connection status indicators

### Port Configuration
Default: `8501`
- Customizable via command line
- Automatic port conflict detection
- Browser auto-launch

### Language Support
- **Korean (ko)**: Default for financial regulations
- **English (en)**: International support
- **Time Hints**: Temporal context support

## Troubleshooting

### Common Issues

**API Not Running**
- Error: "API is not running"
- Solution: Start API server first with `python start.py --api-only`

**Port Conflicts**
- Error: "Port 8501 already in use"
- Solution: Use different port or stop conflicting service

**Dependencies Missing**
- Error: "Module not found"
- Solution: Install requirements with `pip install -r requirements.txt`

### Debug Mode
Enable verbose logging:
```bash
python start.py --chat-only --verbose
```

### Performance Issues
- Check API server response times
- Monitor system resources
- Review trace details in thinking process panel

## Development

### Customization
- **CSS Styling**: Modify custom styles in `chat_gui.py`
- **Sample Queries**: Update Korean financial regulation examples
- **Performance Metrics**: Add custom visualizations
- **Language Support**: Extend multi-language capabilities

### Extending Features
- **File Upload**: Add document upload capability
- **Export Chat**: Save conversation history
- **Advanced Analytics**: Enhanced performance tracking
- **Custom Themes**: Additional UI themes

## Integration

### With API Server
The chat GUI automatically integrates with the Retrieval Agent API:
- **Health Monitoring**: Continuous API status checking
- **Query Processing**: Seamless query submission
- **Response Handling**: Real-time result display
- **Error Management**: Graceful error handling

### With Weaviate
When Weaviate is running:
- **Real Search**: Actual document retrieval
- **Citations**: Genuine source references
- **Performance**: Real response times
- **Analytics**: Actual system metrics

### Without Weaviate (Offline Mode)
When Weaviate is not available:
- **Placeholder Responses**: System still functional
- **Demo Mode**: Showcase interface capabilities
- **Development**: Test UI without backend
- **Training**: Learn system operation

## Best Practices

### Usage
1. **Start API First**: Ensure API server is running
2. **Use Sample Queries**: Test with pre-loaded examples
3. **Monitor Performance**: Watch response time indicators
4. **Check Citations**: Verify source references
5. **Clear Chat**: Reset for new conversations

### Development
1. **Test Both Modes**: With and without Weaviate
2. **Monitor Logs**: Check console output for errors
3. **Update Dependencies**: Keep packages current
4. **Customize Styling**: Adapt to your needs
5. **Add Features**: Extend functionality as needed

The Chat GUI provides a complete, professional interface for interacting with the Retrieval Agent system, making it easy to explore Korean financial regulations with full visibility into the agent's reasoning process.
