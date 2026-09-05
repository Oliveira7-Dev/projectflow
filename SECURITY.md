# Segurança do ProjectFlow

## Proteções implementadas

- Senhas armazenadas somente como hash `scrypt`
- Proteção CSRF em todos os formulários POST
- Rate limit no login e cadastro
- Cookies `HttpOnly`, `SameSite=Lax` e `Secure` em produção
- HTTPS forçado em produção
- Content Security Policy
- HSTS, proteção contra clickjacking e referrer policy
- `SECRET_KEY` e `DATABASE_URL` somente por variáveis de ambiente
- Mensagem de login genérica para evitar enumeração de usuários
- Controle de autorização: cada usuário só acessa seus próprios projetos/tarefas
- Limites de tamanho de entrada
- Validação de status, prioridade, datas e campos
- ORM SQLAlchemy para evitar SQL Injection em consultas comuns
- Logout por POST + CSRF

## Regras importantes

1. Nunca coloque `SECRET_KEY`, senha do banco ou `DATABASE_URL` no GitHub.
2. Ative autenticação de dois fatores no GitHub, Render e Neon.
3. Troque imediatamente qualquer segredo que tenha sido exposto.
4. Mantenha dependências atualizadas.
5. Use apenas HTTPS em produção.
6. Faça backups periódicos do banco.


## Recuperação de senha

- Link assinado com `itsdangerous`
- Expiração em 30 minutos
- Token vinculado ao hash atual da senha
- Token anterior deixa de valer após a troca de senha
- Resposta genérica para não revelar contas existentes
- Rate limit na solicitação e na redefinição
- Envio por SMTP configurado apenas via variáveis de ambiente


## Política de senha

O servidor valida mínimo de 10 caracteres, letra maiúscula, letra minúscula, número e caractere especial. A barra de força no navegador é apenas informativa; a validação real também acontece no backend.


## Verificação de propriedade do e-mail

Novas contas são criadas como não verificadas. O login só é permitido após a confirmação por link temporário enviado ao endereço cadastrado. O reenvio possui rate limit e respostas genéricas para reduzir enumeração de contas.
