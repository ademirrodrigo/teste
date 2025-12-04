# Avaliação do pacote `sped-nfse-amtec` (Goiânia)

Esta análise resume o que o pacote PHP [`nfephp-org/sped-nfse-amtec`](https://github.com/andrentfs/sped-nfse-amtec) oferece e como ele poderia ser integrado ao fluxo atual de emissão de NFS-e via ISSNet Online.

## Características principais do pacote
- **Tecnologia**: biblioteca PHP distribuída via Composer.
- **Padrão**: ABRASF 2.0 com adaptações do modelo AMTEC da Prefeitura de Goiânia.
- **Escopo**: exclusivo para Goiânia/GO (IBGE 5208707, SIAF 9373).
- **Transporte**: SOAP 1.2 com certificado A1 (PFX) no endpoint único `https://nfse.goiania.go.gov.br/ws/nfse.asmx` e namespace `http://nfse.goiania.go.gov.br/xsd/nfse_gyn_v02.xsd`.
- **WSDL/XSD**: publicados em `https://nfse.goiania.go.gov.br/ws/nfse.asmx?wsdl` e `https://nfse.goiania.go.gov.br/xsd/nfse_gyn_v02.xsd`.
- **Métodos disponíveis**: somente `GerarNfse` (um RPS por vez) e `ConsultarNfseRps`.
- **Ambiente**: um único endpoint suporta TESTE e PRODUÇÃO; começa em TESTE e muda para PRODUÇÃO via solicitação por e-mail.
- **Restrições de certificado**: o PFX deve ser emitido para o CNPJ cadastrado na prefeitura (não aceita CNPJ raiz genérico).
- **Limitações**: não há cancelamento via webservice e algumas tags ABRASF 2.0 são proibidas ou opcionais (ex.: `ValorIss`, `ItemListaServico`, `Competencia`, `OptanteSimplesNacional`).

## Implicações para o sistema atual
- O projeto é PHP e depende de Composer/PSR, enquanto o nosso emissor é Python com automação HTTP do ISSNet Online. A integração direta exigiria:
  - **Camada ponte**: expor o pacote via microserviço PHP (container) ou CLI e consumi-lo a partir da nossa CLI Python.
  - **Reimplementação em Python**: replicar os envelopes SOAP usando `zeep`/`requests_pkcs12` com o WSDL público e respeitar as adaptações do XSD (remoção de campos não aceitos).
- O pacote opera com **ambiente sempre de produção** (apenas modo TESTE/PRODUÇÃO no mesmo endpoint). Isso elimina a possibilidade de um ambiente de homologação separado e exige controles claros de modo de envio.
- Como só há **`GerarNfse` síncrono** (sem lote) e **`ConsultarNfseRps`**, continuariam ausentes operações de cancelamento ou consulta por intervalo. O fluxo de download/armazenamento local (já implementado) precisaria consumir a resposta do SOAP.
- O manual reforça que várias tags ABRASF são proibidas ou não retornadas; nosso validador de payload teria de ser ajustado para remover campos como `ValorIss`, `Competencia`, `ItemListaServico` e `OptanteSimplesNacional` antes de montar o XML.

## Passos recomendados caso a integração seja adotada
1. **Escolher a estratégia**: microserviço PHP (Composer) ou reimplementação SOAP em Python.
2. **Mapear payload**: alinhar `NotaServico`/YAML para o layout AMTEC, omitindo os campos proibidos e garantindo obrigatórios (`CodigoTributacaoMunicipio`, `tcCpfCnpj`, `tsInscricaoMunicipal`).
3. **Gerenciar modos**: adicionar flag de TESTE/PRODUÇÃO no cadastro da empresa para enviar o parâmetro correto na requisição SOAP (mantendo endpoint único).
4. **Autenticação**: reutilizar o carregamento PFX (`requests_pkcs12.Pkcs12Adapter`) para assinar as chamadas SOAP 1.2.
5. **Consulta/armazenamento**: após `GerarNfse`, parsear o XML retornado (número, código de verificação) e armazenar em `data/nfse/<CNPJ>/<ANO>/<MES>/`, mantendo compatibilidade com nosso `storage`.
6. **Fallback/convivência**: manter a automação ISSNet atual como fallback até que o fluxo SOAP esteja validado em produção.
