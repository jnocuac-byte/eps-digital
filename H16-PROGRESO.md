# H-16 Progreso
- [x] FASE 0: gh instalado y autenticado (cuenta pardoski1106, permiso WRITE), rama feat/h16-kubernetes creada desde origin/main
- [x] FASE 1: endpoints /health y /ready
- [x] FASE 2: frontend modo gateway + Dockerfile.k8s
- [x] FASE 3: manifiestos k8s/ (rebase sobre origin/develop hecho; base = develop y PR hacia develop; postgres usa pgvector/pgvector:pg15)
- [ ] FASE 4 (devcontainer.json y deploy.sh escritos; falta commit/push, Codespace y despliegue): devcontainer, deploy.sh, Codespace, despliegue
- [ ] FASE 5: evidencias + levantar-demo
- [ ] FASE 6: README, PR, H16-ENTREGA.md

- Codespace creado: eps-h16-77rgx6x5rpgg3wqjr (rama feat/h16-kubernetes, commit 3dae7c9 pusheado)
- Codespace eps-h16-77rgx6x5rpgg3wqjr FALLO (universal:2 llena el disco de 32GB -> contenedor de recuperacion). Se cambia devcontainer a base:ubuntu-22.04 + docker-in-docker + kubectl-helm-minikube y se recrea el Codespace.
- Nuevo Codespace: eps-h16-wv9w4p4599w6cg7jg
- Codespace vigente: eps-h16-6vrjpqp5r49v35q6x (devcontainer base ubuntu + sshd + dind)
- FASE 4: deploy.sh lanzado en el Codespace (log: /tmp/deploy.log)
