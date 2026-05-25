FROM public.ecr.aws/lambda/python:3.12

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY src/ ./

# Lambda handler entrypoint - points to handler = Mangum(app) in webhook.py
CMD ["webhook.handler"]