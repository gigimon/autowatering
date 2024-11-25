FROM python:3.10-slim

RUN mkdir /opt/app
WORKDIR /opt/app

COPY ./* /opt/app/

RUN pip install -r requirements.txt

EXPOSE 8080/tcp
CMD ["python", "app.py"]