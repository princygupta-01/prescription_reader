# Deployment Guide

## Quick Start with Docker Compose

1. **Clone and setup**:
```bash
git clone <your-repo>
cd prescription-reader
cp backend/.env.example backend/.env
```

2. **Add your Groq API key** to `backend/.env`:
```
GROQ_API_KEY=your_groq_api_key_here
```

3. **Run with Docker**:
```bash
docker-compose up --build
```

Access at: http://localhost:3000

## Production Deployment

### Railway (Backend)

1. **Deploy backend**:
```bash
cd backend
railway login
railway new
railway add
```

2. **Set environment variables**:
```bash
railway env set GROQ_API_KEY=your_key_here
railway env set TROCR_MODEL=microsoft/trocr-large-handwritten
railway env set DATABASE_URL=sqlite:///./prescriptions.db
```

3. **Note**: TrOCR model (1.3GB) will be cached in `/app/model_cache/`

### Vercel (Frontend)

1. **Deploy frontend**:
```bash
cd frontend
npm install
vercel
```

2. **Set environment variable**:
```bash
vercel env add NEXT_PUBLIC_API_URL
# Enter your Railway backend URL
```

### HuggingFace Spaces (Alternative Backend)

For free GPU access, deploy to HuggingFace Spaces:

1. Create new Space with Python SDK
2. Upload all backend files
3. Add `app.py` with Gradio interface
4. Set secrets: `GROQ_API_KEY`

Benefits:
- Free T4 GPU (10x faster TrOCR inference)
- No cold starts
- Automatic scaling

## Environment Variables

### Backend (.env)
```
GROQ_API_KEY=your_groq_api_key_here
DATABASE_URL=sqlite:///./prescriptions.db
GROQ_MODEL=llama-3.2-3b-instruct
TROCR_MODEL=microsoft/trocr-large-handwritten
OPENFDA_BASE=https://api.fda.gov/drug/label.json
```

### Frontend
```
NEXT_PUBLIC_API_URL=https://your-backend-url.railway.app
```

## Performance Optimization

### Model Caching
- TrOCR model (1.3GB) downloads on first use
- Cached in `/app/model_cache/` or `~/.cache/huggingface/`
- Subsequent starts are instant

### Database
- SQLite for development
- Consider PostgreSQL for production with high volume
- Database migrations handled automatically

### Scaling
- Backend: Stateless, can run multiple instances
- Frontend: Static files, CDN-friendly
- Model inference: CPU-bound, consider GPU deployment

## Monitoring

### Health Checks
- Backend: `GET /health`
- Returns model status and database connectivity

### Metrics
- Processing statistics: `GET /api/stats`
- Tracks accuracy, processing times, failure rates

### Logs
- Structured logging with processing stages
- Error tracking for failed extractions
- Performance monitoring per pipeline stage

## Security

### API Keys
- Store Groq API key securely
- Use environment variables, never commit keys
- Rotate keys regularly

### File Uploads
- 10MB file size limit
- Image format validation
- Temporary file cleanup

### CORS
- Currently allows all origins (development)
- Restrict in production to your domain

## Troubleshooting

### Common Issues

1. **TrOCR model download fails**:
   - Check internet connection
   - Verify disk space (1.3GB needed)
   - Try manual download: `huggingface-cli download microsoft/trocr-large-handwritten`

2. **Groq API errors**:
   - Verify API key is correct
   - Check rate limits (free tier: 30 requests/minute)
   - Monitor usage at console.groq.com

3. **Poor OCR accuracy**:
   - Ensure image is high quality (>800px)
   - Check image is properly oriented
   - Verify handwriting is clear

4. **PDF generation fails**:
   - Check reportlab installation
   - Verify font availability
   - Check disk space for temporary files

### Performance Issues

1. **Slow processing**:
   - TrOCR on CPU takes 8-12 seconds
   - Consider GPU deployment for 1-2 second inference
   - Check if model is properly cached

2. **Memory usage**:
   - TrOCR model uses ~2GB RAM
   - Consider model quantization for lower memory
   - Monitor container memory limits

### Getting Help

1. Check logs for detailed error messages
2. Verify all environment variables are set
3. Test with sample prescription images
4. Check model and API connectivity with `/health` endpoint