# =======================================================
# MAKEFILE POUR LE PROJET OPENAI AGENTS
# =======================================================

.PHONY: help install start test clean docs

# Variables
API_DIR = api
FRONTEND_DIR = frontend
PYTHON = python3
PIP = pip3
UV = uv
NPM = npm

# Couleurs pour les messages
GREEN = \033[0;32m
YELLOW = \033[1;33m
RED = \033[0;31m
NC = \033[0m # No Color

help: ## Affiche l'aide
	@echo "$(GREEN)🏢 OpenAiAgents - Extraction d'Informations d'Entreprise$(NC)"
	@echo "=================================================="
	@echo ""
	@echo "$(YELLOW)Commandes disponibles:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(YELLOW)Structure du projet:$(NC)"
	@echo "  📓 Notebooks d'expérimentation (racine)"
	@echo "  🚀 API de production (dossier api/)"
	@echo "  🌐 Frontend Next.js (dossier frontend/)"
	@echo ""

install: ## Installe les dépendances avec uv
	@echo "$(GREEN)📦 Installation des dépendances avec uv...$(NC)"
	$(UV) sync
	@echo "$(GREEN)✅ Installation terminée$(NC)"

install-api: ## Installe les dépendances de l'API (via uv au niveau racine)
	@echo "$(GREEN)📦 Installation des dépendances de l'API (uv sync racine)...$(NC)"
	$(UV) sync
	@echo "$(GREEN)✅ Installation API terminée$(NC)"

install-dev: ## Installe les dépendances de développement
	@echo "$(GREEN)📦 Installation des dépendances de développement...$(NC)"
	$(UV) sync --dev
	@echo "$(GREEN)✅ Installation dev terminée$(NC)"

install-frontend: ## Installe les dépendances du frontend (si package.json présent)
	@echo "$(GREEN)📦 Installation des dépendances du frontend...$(NC)"
	@if [ -f "$(FRONTEND_DIR)/package.json" ]; then \
		cd $(FRONTEND_DIR) && $(NPM) install && echo "$(GREEN)✅ Installation frontend terminée$(NC)"; \
	else \
		echo "$(YELLOW)⚠️ Aucun package.json dans $(FRONTEND_DIR) — étape ignorée$(NC)"; \
	fi

install-all: install install-frontend ## Installe toutes les dépendances (API + Frontend)
	@echo "$(GREEN)✅ Toutes les dépendances installées$(NC)"

start: ## Démarre l'API avec uv
	@echo "$(GREEN)🚀 Démarrage de l'API avec uv...$(NC)"
	$(UV) run --directory $(API_DIR) python start.py

start-bg: ## Démarre l'API en arrière-plan avec uv
	@echo "$(GREEN)🚀 Démarrage de l'API en arrière-plan avec uv...$(NC)"
	$(UV) run --directory $(API_DIR) nohup python start.py > api.log 2>&1 &
	@echo "$(GREEN)✅ API démarrée en arrière-plan (PID: $$!)$(NC)"
	@echo "$(YELLOW)📋 Logs: $(API_DIR)/api.log$(NC)"

start-frontend: ## Démarre le frontend en mode développement
	@echo "$(GREEN)🌐 Démarrage du frontend...$(NC)"
	cd $(FRONTEND_DIR) && $(NPM) run dev

start-frontend-bg: ## Démarre le frontend en arrière-plan
	@echo "$(GREEN)🌐 Démarrage du frontend en arrière-plan...$(NC)"
	cd $(FRONTEND_DIR) && nohup $(NPM) run dev > frontend.log 2>&1 &
	@echo "$(GREEN)✅ Frontend démarré en arrière-plan$(NC)"

start-all: ## Démarre l'API et le frontend
	@echo "$(GREEN)🚀 Démarrage complet (API + Frontend)...$(NC)"
	@$(MAKE) start-bg
	@sleep 2
	@$(MAKE) start-frontend

test: ## Vérifie l’API via healthcheck
	@echo "$(GREEN)🧪 Healthcheck API...$(NC)"
	@if curl -fsS http://localhost:8000/health > /dev/null; then \
		echo "$(GREEN)✅ API OK$(NC)"; \
	else \
		echo "$(RED)❌ API KO$(NC)"; exit 1; \
	fi

test-frontend: ## Lance les tests du frontend
	@echo "$(GREEN)🧪 Lancement des tests du frontend...$(NC)"
	cd $(FRONTEND_DIR) && $(NPM) test

build-frontend: ## Build le frontend pour production
	@echo "$(GREEN)🏗️ Build du frontend...$(NC)"
	cd $(FRONTEND_DIR) && $(NPM) run build
	@echo "$(GREEN)✅ Build frontend terminé$(NC)"

demo: ## Lance la démonstration avec uv
	@echo "$(GREEN)🎯 Lancement de la démonstration avec uv...$(NC)"
	$(UV) run --directory $(API_DIR) python demo.py

stop: ## Arrête l'API en arrière-plan
	@echo "$(YELLOW)🛑 Arrêt de l'API...$(NC)"
	@pkill -f "python.*start.py" || echo "$(YELLOW)⚠️ Aucune API en cours d'exécution$(NC)"

stop-frontend: ## Arrête le frontend en arrière-plan
	@echo "$(YELLOW)🛑 Arrêt du frontend...$(NC)"
	@pkill -f "npm.*run.*dev" || echo "$(YELLOW)⚠️ Aucun frontend en cours d'exécution$(NC)"

stop-all: ## Arrête l'API et le frontend
	@echo "$(YELLOW)🛑 Arrêt complet (API + Frontend)...$(NC)"
	@$(MAKE) stop
	@$(MAKE) stop-frontend

status: ## Vérifie le statut de l'API et du frontend
	@echo "$(GREEN)🔍 Vérification du statut...$(NC)"
	@echo "$(YELLOW)API:$(NC)"
	@if curl -s http://localhost:8000/health > /dev/null; then \
		echo "$(GREEN)✅ API disponible sur http://localhost:8000$(NC)"; \
		echo "$(GREEN)📚 Documentation: http://localhost:8000/docs$(NC)"; \
	else \
		echo "$(RED)❌ API non disponible$(NC)"; \
	fi
	@echo "$(YELLOW)Frontend:$(NC)"
	@if curl -s http://localhost:3000 > /dev/null 2>&1 || curl -s http://localhost:3001 > /dev/null 2>&1; then \
		echo "$(GREEN)✅ Frontend disponible sur http://localhost:3000 ou http://localhost:3001$(NC)"; \
	else \
		echo "$(RED)❌ Frontend non disponible$(NC)"; \
	fi
	@echo "$(YELLOW)💡 Démarrez tout avec: make start-all$(NC)"

clean: ## Nettoie les fichiers temporaires
	@echo "$(YELLOW)🧹 Nettoyage des fichiers temporaires...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.log" -delete
	find . -type f -name "*.tmp" -delete
	@if [ -d "$(FRONTEND_DIR)/.next" ]; then rm -rf $(FRONTEND_DIR)/.next; fi
	@if [ -d "$(FRONTEND_DIR)/node_modules/.cache" ]; then rm -rf $(FRONTEND_DIR)/node_modules/.cache; fi
	@echo "$(GREEN)✅ Nettoyage terminé$(NC)"

docs: ## Ouvre la documentation de l'API
	@echo "$(GREEN)📚 Ouverture de la documentation...$(NC)"
	@if curl -s http://localhost:8000/health > /dev/null; then \
		open http://localhost:8000/docs; \
	else \
		echo "$(RED)❌ API non disponible$(NC)"; \
		echo "$(YELLOW)💡 Démarrez avec: make start$(NC)"; \
	fi

logs: ## Affiche les logs de l'API
	@echo "$(GREEN)📋 Affichage des logs...$(NC)"
	@if [ -f "$(API_DIR)/api.log" ]; then \
		tail -f $(API_DIR)/api.log; \
	else \
		echo "$(YELLOW)⚠️ Aucun fichier de log trouvé$(NC)"; \
	fi

setup: install install-frontend ## Configuration complète du projet (uv backend + npm frontend)
	@echo "$(GREEN)🔧 Configuration du projet avec uv...$(NC)"
	@if [ -z "$$OPENAI_API_KEY" ]; then \
		echo "$(YELLOW)⚠️ OPENAI_API_KEY non définie$(NC)"; \
		echo "$(YELLOW)💡 Définissez votre clé API:$(NC)"; \
		echo "$(YELLOW)   export OPENAI_API_KEY='votre-cle-api'$(NC)"; \
	fi
	@echo "$(GREEN)✅ Configuration terminée$(NC)"

sync: ## Synchronise les dépendances avec uv
	@echo "$(GREEN)🔄 Synchronisation des dépendances...$(NC)"
	$(UV) sync
	@echo "$(GREEN)✅ Synchronisation terminée$(NC)"

add: ## Ajoute une dépendance avec uv (usage: make add package=requests)
	@echo "$(GREEN)📦 Ajout de la dépendance: $(package)$(NC)"
	$(UV) add $(package)
	@echo "$(GREEN)✅ Dépendance ajoutée$(NC)"

remove: ## Supprime une dépendance avec uv (usage: make remove package=requests)
	@echo "$(YELLOW)🗑️ Suppression de la dépendance: $(package)$(NC)"
	$(UV) remove $(package)
	@echo "$(GREEN)✅ Dépendance supprimée$(NC)"

lock: ## Génère le fichier de verrouillage avec uv
	@echo "$(GREEN)🔒 Génération du fichier de verrouillage...$(NC)"
	$(UV) lock
	@echo "$(GREEN)✅ Fichier de verrouillage généré$(NC)"

# Commandes de monitoring des quotas
credits: ## Affiche les crédits OpenAI restants
	@echo "$(GREEN)💳 Crédits OpenAI...$(NC)"
	@curl -s http://localhost:8000/credits | python -m json.tool || echo "$(RED)❌ API non disponible$(NC)"

# Commandes Docker
docker-build: ## Construit toutes les images Docker (API + Frontend)
	@echo "$(GREEN)🐳 Construction des images Docker...$(NC)"
	docker-compose build --no-cache
	@echo "$(GREEN)✅ Images Docker construites$(NC)"

docker-build-api: ## Construit uniquement l'image Docker de l'API
	@echo "$(GREEN)🐳 Construction de l'image Docker API...$(NC)"
	docker-compose build --no-cache api

docker-build-frontend: ## Construit uniquement l'image Docker du frontend
	@echo "$(GREEN)🐳 Construction de l'image Docker Frontend...$(NC)"
	docker-compose build --no-cache frontend

docker-start: ## Démarre tous les services avec Docker
	@echo "$(GREEN)🐳 Démarrage des services avec Docker...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✅ Services démarrés$(NC)"
	@echo "$(YELLOW)🌐 Frontend: http://localhost:3000$(NC)"
	@echo "$(YELLOW)🚀 API: http://localhost:8000$(NC)"
	@echo "$(YELLOW)📚 Documentation: http://localhost:8000/docs$(NC)"

docker-start-api: ## Démarre uniquement l'API avec Docker
	@echo "$(GREEN)🐳 Démarrage de l'API avec Docker...$(NC)"
	docker-compose up -d api

docker-start-frontend: ## Démarre uniquement le frontend avec Docker
	@echo "$(GREEN)🐳 Démarrage du frontend avec Docker...$(NC)"
	docker-compose up -d frontend

docker-stop: ## Arrête tous les services Docker
	@echo "$(YELLOW)🛑 Arrêt des services Docker...$(NC)"
	docker-compose down

docker-restart: ## Redémarre tous les services Docker
	@echo "$(GREEN)🔄 Redémarrage des services Docker...$(NC)"
	docker-compose restart

docker-logs: ## Affiche les logs Docker
	@echo "$(GREEN)📋 Affichage des logs Docker...$(NC)"
	docker-compose logs -f

docker-logs-api: ## Affiche les logs de l'API
	@echo "$(GREEN)📋 Affichage des logs API...$(NC)"
	docker-compose logs -f api

docker-logs-frontend: ## Affiche les logs du frontend
	@echo "$(GREEN)📋 Affichage des logs frontend...$(NC)"
	docker-compose logs -f frontend

docker-clean: ## Nettoie les conteneurs et images Docker
	@echo "$(YELLOW)🧹 Nettoyage Docker...$(NC)"
	docker-compose down --volumes --remove-orphans --rmi local
	@echo "$(GREEN)✅ Nettoyage Docker terminé$(NC)"

docker-status: ## Affiche le statut des conteneurs
	@echo "$(GREEN)🔍 Statut des conteneurs...$(NC)"
	docker-compose ps

# Alias pour les commandes courantes
run: start ## Alias pour start
serve: start ## Alias pour start
check: status ## Alias pour status
