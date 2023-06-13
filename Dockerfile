FROM tiangolo/uwsgi-nginx-flask:python3.8
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt
COPY . /app
ENV LISTEN_PORT 8080
EXPOSE 8080
ENV STATIC_PATH /app/frontend/static
RUN chown -R nginx /app
#CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]
