import requests

# URL da API
url = ''

# Dados a serem enviados
dados = {
    'owner_name': 'Nome do Proprietário',
    'issuer_name': 'Nome do Emissor'
}

# Realizar a chamada POST
response = requests.post(url, json=dados)

# Verificar o status da resposta
if response.status_code == 200:
    print('Badge emitido com sucesso!')
    print('Resposta:', response.json())
else:
    print('Erro ao emitir badge. Status:', response.status_code)