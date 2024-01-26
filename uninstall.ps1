$resourceGroupName=Read-Host "Qual o RG que deseja excluir?"
az group delete --name $resourceGroupName