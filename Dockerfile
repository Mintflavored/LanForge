# Multi-stage ultra-light build for LANForge Signaling Server
FROM golang:1.24-alpine AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o /lanforge-server ./cmd/server

# Final scratch runtime (only ~12MB)
FROM alpine:latest
RUN apk --no-cache add ca-certificates tzdata

WORKDIR /root/
COPY --from=builder /lanforge-server .

EXPOSE 8787
ENV PORT=8787

CMD ["./lanforge-server", "-port", "8787"]
