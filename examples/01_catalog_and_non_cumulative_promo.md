# Exemplo 1: Busca de Catálogo (Violões até R$ 1.000) e Regra de Promoção Não Cumulativa no PIX

**Cenário:** O cliente pede opções de violões disponíveis até R$ 1.000,00. Em seguida, pergunta o preço do **Takamine GD20** e do **Taylor 110e**, questionando se ambos recebem os 5% de desconto no PIX e como funciona o parcelamento.

---

### Turno 1 — Consulta de Catálogo com Filtro de Preço e Disponibilidade

**🧑 Cliente:**
> Olá! Quais opções de violões disponíveis vocês têm custando até R$ 1.000?

**🛠️ Ferramenta Acionada pelo Agente:**
* `search_products_catalog(query="violão", category_name="Violões", max_price_brl=1000.0, only_available=True)`

**🎸 Assistente Empório da Música:**
> Olá! Tudo bem? 🎶 Seja muito bem-vindo(a) à **Empório da Música**! Temos ótimas opções de violões em estoque hoje na faixa de até R$ 1.000,00, tanto com cordas de nylon quanto de aço (e até de 7 cordas!). Dá uma olhada nos modelos disponíveis para pronta-entrega:
>
> **Violões de Nylon (Clássicos):**
> 1. **Tagima Memphis AC-39 Nylon Natural** — **R$ 429,90** (ou **R$ 408,40** à vista no PIX com 5% de desconto) | *15 un. em estoque*
> 2. **Rozini RC-104 Nylon Estudante** — **R$ 459,90** (ou **R$ 436,90** no PIX) | *10 un. em estoque*
> 3. **Yamaha C40 Nylon Natural** — **R$ 599,90** (ou **R$ 569,90** no PIX) | *12 un. em estoque*
> 4. **Giannini GN-15 Nylon Cedro Natural** — **R$ 689,00** (ou **R$ 654,55** no PIX) | *6 un. em estoque*
> 5. **Yamaha C70 Nylon Natural** (tampo sólido) — **R$ 849,00** (ou **R$ 806,55** no PIX) | *8 un. em estoque*
>
> **Violões de Aço (Folk / Dreadnought / Eletroacústico):**
> 6. **Shelby SN-100 Folk Aço Preto** — **R$ 549,00** (ou **R$ 521,55** no PIX) | *5 un. em estoque*
> 7. **Giannini GF-1R Aço Folk Sunburst** — **R$ 579,90** (ou **R$ 550,90** no PIX) | *7 un. em estoque*
> 8. **Yamaha F310 Aço Natural** — **R$ 699,90** (ou **R$ 664,90** no PIX) | *14 un. em estoque*
> 9. **Tagima Dallas Tuner Aço Natural** (com afinador) — **R$ 749,00** (ou **R$ 711,55** no PIX) | *9 un. em estoque*
> 10. **Shelby SGD-195E Elétrico Aço Sunburst** (eletroacústico) — **R$ 799,00** (ou **R$ 759,05** no PIX) | *6 un. em estoque*
> 11. **Tagima Woodstock Dreadnought Natural** — **R$ 899,00** (ou **R$ 854,05** no PIX) | *11 un. em estoque*
>
> **Violão de 7 Cordas:**
> 12. **Tagima TW-7 7 Cordas Aço Natural** — **R$ 999,00** (ou **R$ 949,05** no PIX) | *6 un. em estoque*
>
> *(Nota: O modelo Giannini GF-3D de R$ 799,90 e o Shelby SN-7C de R$ 749,00 não foram listados pois estão sem estoque/descontinuados no momento).*
>
> Você prefere cordas de **nylon** (mais macias para começar ou tocar MPB/clássico) ou de **aço** (som mais brilhante e encorpado)?

---

### Turno 2 — Consulta de Preço Específico, Promoção Ativa vs. Expirada e Regra do PIX

**🧑 Cliente:**
> Legal! E subindo um pouco o orçamento: quanto custam o Takamine GD20 e o Taylor 110e? Se eu pagar no PIX ganho os 5% de desconto nos dois?

**🛠️ Ferramentas Acionadas pelo Agente:**
* `search_products_catalog(query="Takamine GD20")`
* `search_products_catalog(query="Taylor 110e")`
* `calculate_payment_and_shipping(amount_brl=2199.0, has_active_promotion=False, city="Campo Grande")`
* `calculate_payment_and_shipping(amount_brl=5519.08, has_active_promotion=True, city="Campo Grande")`

**🎸 Assistente Empório da Música:**
> Excelentes escolhas! Ambos são violões dreadnought de tampo sólido incríveis e estão disponíveis em estoque, mas há uma diferença importante na aplicação do desconto do PIX entre eles por conta das nossas regras de promoção:
>
> ### 1. Takamine GD20 Dreadnought Natural (*5 unidades em estoque*)
> * **Preço de Tabela:** **R$ 2.199,00** *(ele teve uma campanha anterior de 12%, mas já está encerrada)*
> * **No PIX (5% de desconto aplicado):** **R$ 2.089,05** (economia de R$ 109,95!)
> * **No Cartão de Crédito:** em até **12x sem juros de R$ 183,25**
>
> ### 2. Taylor 110e Dreadnought Natural — Eletroacústico ES2 (*4 unidades em estoque*)
> * **Preço Original de Tabela:** R$ 5.999,00
> * **Promoção Ativa (*Desconto Exclusivo - 8% OFF*):** **R$ 5.519,08**
> * **No PIX:** **R$ 5.519,08** — como o Taylor 110e **já está com 8% de desconto promocional ativo**, os 5% do PIX **não se acumulam** (pela política da loja, descontos não são cumulativos, então você já garante o abatimento maior de 8%!).
> * **No Cartão de Crédito:** em até **12x sem juros de R$ 459,92**
>
> Além disso, como ambos passam de **R$ 2.000,00**, você também pode **combinar formas de pagamento** (por exemplo, dar uma entrada via PIX e parcelar o restante no cartão), e para entregas na Região Metropolitana de Campo Grande o **frete por motoboy é grátis** (compras acima de R$ 500,00)! Qual dos dois combina mais com o som que você procura?
