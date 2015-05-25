FROM gliderlabs/alpine:3.1

MAINTAINER Allan Costa "allan@cloudwalk.io"

RUN apk --update add python py-pip && rm -rf /var/cache/apk/*

WORKDIR /src/fleet-browser
COPY . /src/fleet-browser

RUN pip install -r requirements.txt

EXPOSE 5000

ENTRYPOINT ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
