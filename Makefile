.PHONY: default tests clean

default: run_zk_docker
	@echo "Starting NFS server and client..."
	@bash -c '\
		python -m nfs.server & \
		SERVER_PID=$$!; \
		trap "echo Stopping NFS server...; kill $$SERVER_PID" EXIT; \
		python -m nfs.client \
	'

run_zk_docker:
	@docker compose up -d

tests:
	@echo "Running unit tests..."
	@python -m unittest discover test

clean:
	@echo "Cleaning up..."
	@rm -rf ./storage
	@rm -f ./persist
	@echo "Cleaned up storage and persist."
