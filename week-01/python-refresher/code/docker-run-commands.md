## Pull the image from docker hub

```bash
docker pull ram1uj/study-buddy:v1
```

## Run directly with docker run

```bash
docker run -d -p 8000:8000 --name study-buddy ram1uj/study-buddy:v1
```

## Alternatevely, you can use docker-compose to run the container. Make sure you have the `docker-compose.yaml` file in the current directory.  

```bash
docker-compose up -d
```