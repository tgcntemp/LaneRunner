TIMESTAMP = date +%Y%m%d%H%M%S

run:
	@echo "========== Running the LaneRunner project... =========="
	@${MAKE} install
	@${MAKE} start
	

install:
	@echo "========== Setting up the environment... =========="
	python3.7 -m venv venv && \
	. venv/bin/activate && pip install --upgrade pip && \
	. ./environment.sh && \
	echo "===== Environment setup complete. =====" && \
	echo "===== Installing dependencies... =====" && \
	pip install -r requirements.txt && \
	echo "===== Dependencies installed. =====" && \
	echo "===== Start the project with 'make start' ====="

start:
	@echo "========== Starting Carla Server and Client... =========="
	@${MAKE} server
	@${MAKE} client
	@${MAKE} traffic

server:
	@echo "========== Starting Carla Server... =========="
	@chmod +x environment.sh
	@mkdir -p logs
	@LOGFILE=logs/$$($(TIMESTAMP))-server.log; \
	bash -c '\
		set -e; \
		. venv/bin/activate; \
		. ./environment.sh; \
		echo "===== CARLA_ROOT is set to $$CARLA_ROOT ====="; \
		nohup $$CARLA_ROOT/CarlaUE4.sh -Log --qualityLevel=low > '"$$LOGFILE"' 2>&1 & \
		sleep 10; \
		PID=$$(pgrep -f "CarlaUE4-Linux-Shipping"); \
		echo $$PID > .carla_server.pid; \
		echo "===== Carla Server started with PID: $$PID ====="; \
	'

traffic:
	@echo "========== Running Carla Generate Traffic... =========="
	@chmod +x environment.sh
	@mkdir -p logs
	@LOGFILE=logs/$$($(TIMESTAMP))-traffic.log; \
	bash -c '\
		set -e; \
		. venv/bin/activate; \
		. ./environment.sh; \
		nohup python3.7 src/engine/generate_traffic.py -n 150 -w 0 --safe --sync > '"$$LOGFILE"' 2>&1 & \
		sleep 15; \
		PID=$$(pgrep -f "python3.7"); \
		echo $$PID > .carla_traffic.pid; \
		echo "===== Carla Traffic started with PID: $$PID ====="; \
	'

client:
	@echo "========== Starting Carla Client... =========="
	@chmod +x environment.sh
	@mkdir -p logs
	@LOGFILE=logs/$$($(TIMESTAMP))-client.log; \
	bash -c '\
		set -e; \
		. venv/bin/activate; \
		. ./environment.sh; \
		echo "===== CARLA_ROOT is set to $$CARLA_ROOT ====="; \
		nohup python3.7 lane_runner.py -r 1920x1080 -v > '"$$LOGFILE"' 2>&1 & \
		sleep 20; \
		PID=$$(pgrep -f "python3.7"); \
		echo $$PID > .carla_client.pid; \
		echo "===== Carla Client started with PID: $$PID ====="; \
	'

stop:
	@echo "========== Stopping Carla Client and Server... =========="
	@${MAKE} stop-client
	@${MAKE} stop-traffic
	@${MAKE} stop-server
	@echo "===== All processes stopped. ====="

stop-server:
	@if [ -f .carla_server.pid ]; then \
		PIDS=$$(cat .carla_server.pid); \
		for PID in $$PIDS; do \
			if kill -0 $$PID 2>/dev/null; then \
				kill -TERM $$PID && echo "===== Stopped Carla Server (PID $$PID) ====="; \
			else \
				echo "===== Server PID $$PID not running or already stopped. ====="; \
			fi; \
		done; \
		rm -f .carla_server.pid; \
	else \
		kill -9 $(lsof -t -i:2000); \
		echo "===== No server PID file found. ====="; \
	fi

stop-client:
	@if [ -f .carla_client.pid ]; then \
		PID=$$(cat .carla_client.pid); \
		if kill -0 $$PID 2>/dev/null; then \
			kill -TERM $$PID && echo "===== Stopped Carla Client (PID $$PID) ====="; \
		else \
			echo "===== Client PID $$PID not running. Removing stale PID file. ====="; \
		fi; \
		rm -f .carla_client.pid; \
	else \
		echo "===== No client PID file found. ====="; \
	fi

stop-traffic:
	@if [ -f .carla_traffic.pid ]; then \
		PID=$$(cat .carla_traffic.pid); \
		if kill -0 $$PID 2>/dev/null; then \
			kill -TERM $$PID && echo "===== Stopped Carla Traffic (PID $$PID) ====="; \
		else \
			echo "===== Traffic PID $$PID not running. Removing stale PID file. ====="; \
		fi; \
		rm -f .carla_traffic.pid; \
	else \
		echo "===== No traffic PID file found. ====="; \
	fi

clean:
	@echo "========== Cleaning up the project... =========="
	@${MAKE} stop || true
	@echo "===== Removing __pycache__ directories... ====="
	@find . -depth -type d -name "__pycache__" -exec rm -r {} +
	@echo "===== Cleaning cache directory contents (excluding .gitkeep)... ====="
	@if [ -d cache ]; then find cache -mindepth 1 ! -name ".gitkeep" -exec rm -rf {} +; fi
	@echo "===== Removing venv directory... ====="
	@if [ -d venv ]; then rm -rf venv; fi
	@echo "===== Removing PID files... ====="
	@rm -f .carla_client.pid .carla_server.pid
	@echo "===== Cleanup complete. ====="

clean-logs:
	@echo "========== Cleaning up logs directory... =========="
	@if [ -d logs ]; then rm -rf logs; fi
	@echo "===== Logs directory cleaned. ====="

clear:
	@echo "========== Clearing the project... =========="
	@${MAKE} clean
	@${MAKE} clean-logs
	@echo "===== Project cleared. ====="

push:
	@echo "========== Pushing changes to Git... =========="
	git add .
	git commit -m "Update for Session $(shell date +%Y-%m-%d) at $(shell date +%H:%M:%S)"
	git push origin main
	@echo "===== Changes pushed to Git. ====="