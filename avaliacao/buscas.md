# Buscas de avaliação da PoC (congeladas)

> Conjunto final: **7 buscas**. Este arquivo vai para o commit **antes** de existir código de busca, e depois disso
> não é mais editado. O protocolo completo está em `docs/etapa-0-poc.md`, seção 9.

- **Avaliador:** Caio
- **Pasta raiz indexada:** Meu Drive
- **ID da pasta raiz:** root
- **Data em que foi congelado:** 2026-09-25

## Regras de preenchimento

1. **Descrição e consulta** se escrevem **de memória, sem abrir o Drive**.
2. A **consulta** é exatamente o que você digitaria primeiro. Ela vai ser idêntica no
   Drive e no app, e as reformulações ficam para a hora do teste.
3. Não escolha buscas pensando no que o app faria bem. Use o que você realmente
   precisou achar.
4. Só **depois** de escrever descrição e consulta, localize o arquivo **navegando pelas
   pastas, sem usar a busca**, e preencha o gabarito.
5. O ID do arquivo fica na URL, depois de `/d/` ou de `id=`.
6. Se o alvo estiver **fora da pasta raiz**, troque a busca.
7. **Tipo esperado** é um destes: `jpg`, `png`, `pdf`, `docx`, `txt` ou `gdoc`.
8. **Consulta descritiva** (opcional): como você gostaria de buscar, descrevendo o
   arquivo em vez de lembrar o nome. Roda à parte, só no app, e **não entra no placar**.
9. **Sei o nome do arquivo?** Responda sim ou não. O placar é separado por esse campo,
   porque é nas buscas "não" que o app deveria ganhar.

---

## B01
- **O que procuro:** Meu cartão CNPJ.
- **Consulta (tentativa 1):** `CNPJ`
- **Consulta descritiva (diagnóstico):** `cartão CNPJ`
- **Sei o nome do arquivo?** sim
- **Tipo esperado:** pdf
- **Gabarito:** ID `1BmYxwrI2_u4gQcUvbAHJIQEXsuW6PAnj` · caminho `Meu Drive/EMPRESA`

## B02
- **O que procuro:** Imagem pra currículo (versão gerada por IA).
- **Consulta (tentativa 1):** `IMG IA`
- **Consulta descritiva (diagnóstico):** `Imagem pra curriculo IA`
- **Sei o nome do arquivo?** não
- **Tipo esperado:** jpg
- **Gabarito:** ID `1uy_0HWALu4ioD0kN9_QCwxy2TTVXpqsq` · caminho `Meu Drive/Curriculo`

## B03
- **O que procuro:** Imagem pra currículo (versão foto real).
- **Consulta (tentativa 1):** `IMG real`
- **Consulta descritiva (diagnóstico):** `Imagem pra curriculo real`
- **Sei o nome do arquivo?** não
- **Tipo esperado:** jpg
- **Gabarito:** ID `1HyYcIkdxMuXnczhdUUIvsKff0v5uLqjV` · caminho `Meu Drive/Curriculo`

## B04
- **O que procuro:** Currículo criativo.
- **Consulta (tentativa 1):** `Criativo`
- **Consulta descritiva (diagnóstico):** `Curriculo criativo`
- **Sei o nome do arquivo?** sim
- **Tipo esperado:** pdf
- **Gabarito:** ID `1MV7Ue0IofHnLIz8dHU_6UiHx4i7mXVJ8` · caminho `Meu Drive/Curriculo`

## B05
- **O que procuro:** Currículo ATS.
- **Consulta (tentativa 1):** `ATS`
- **Consulta descritiva (diagnóstico):** `Curriculo ATS`
- **Sei o nome do arquivo?** sim
- **Tipo esperado:** pdf
- **Gabarito:** ID `1OEfKfRI_cLK0SUqpy6l4G6GstDo63rKT` · caminho `Meu Drive/Curriculo`

## B06
- **O que procuro:** Foto do casamento dos meus pais.
- **Consulta (tentativa 1):** `Imagem do casamento dos meus pais`
  *(não há consulta natural: "não faço ideia". A descritiva é usada como tentativa 1
  nas duas ferramentas.)*
- **Consulta descritiva (diagnóstico):** `Imagem do casamento dos meus pais`
- **Sei o nome do arquivo?** não
- **Tipo esperado:** jpg
- **Gabarito:** ID `1K5tvYN-9wS-PwZpNJ9nzTyf8JW9L1_eZ` · caminho `Meu Drive/Backups/Backup PC - Talyta`

## B07
- **O que procuro:** Foto minha na frente de um Jetta.
- **Consulta (tentativa 1):** `Jetta imagens`
  *(não há consulta natural: "não faço ideia". A descritiva é usada como tentativa 1
  nas duas ferramentas.)*
- **Consulta descritiva (diagnóstico):** `Jetta imagens`
- **Sei o nome do arquivo?** não
- **Tipo esperado:** jpg
- **Gabarito:** ID `16ykF0UUNK6GC3GC5EjG9HjMBrgxBxpXI` · caminho `Meu Drive/Backups/Backup Celular`

---

## Distribuição (sem ajustar as buscas)

O conjunto tem **7 buscas**, por decisão do avaliador: "esses são os principais
arquivos".

| Tipo | Quantidade |
| --- | --- |
| jpg / png | 4 (B02, B03, B06, B07) |
| pdf | 3 (B01, B04, B05) |
| docx / txt / gdoc | 0 |

| Sei o nome do arquivo? | Quantidade |
| --- | --- |
| sim | 3 (B01, B04, B05) |
| não | 4 (B02, B03, B06, B07) |
