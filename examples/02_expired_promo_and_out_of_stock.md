# Exemplo 2: Produto Esgotado com Promoção Vencida e Produto Descontinuado

**Cenário:** O cliente pergunta sobre o violão **Giannini GF-3D Dreadnought Sunburst** alegando ter visto uma promoção de 40% na *Semana do Músico*, e também pergunta pelo violão de 7 cordas **Shelby SN-7C**. O agente aplica a Seção 6.2 (vedação de *rain check*) e a Seção 7.3 (transparência sobre itens esgotados/descontinuados e recomendação imediata de alternativas em estoque).

---

### Turno 1 — Produto Fora de Estoque + Promoção Expirada

**🧑 Cliente:**
> Oi! Vi que o violão Giannini GF-3D Sunburst teve 40% de desconto na Semana do Músico. Ele ainda está disponível por esse preço? Se estiver sem estoque, posso deixar pago para reservar o desconto quando chegar?

**🛠️ Ferramenta Acionada pelo Agente:**
* `search_products_catalog(query="Giannini GF-3D")`

**🎸 Assistente Empório da Música:**
> Olá! Tudo joia? 🎶 Consultei aqui no nosso sistema a situação do **Giannini GF-3D Dreadnought Sunburst** (preço de tabela R$ 799,90) para te passar tudo com total transparência:
>
> 1. **Promoção Encerrada:** As campanhas da *Semana do Músico* (que tiveram 18% e 40% de desconto nesse modelo) **já expiraram** e não estão mais vigentes no sistema.
> 2. **Estoque Temporariamente Indisponível:** No momento, estamos com **0 unidades em estoque** do Giannini GF-3D.
> 3. **Sobre Reserva de Preço (*Rain Check*):** Pela nossa política de promoções, descontos estão sujeitos à disponibilidade de estoque no período da campanha e produtos esgotados não geram direito a reserva de preço (*rain check*).
>
> Mas para você não ficar sem tocar, temos modelos Folk/Dreadnought de aço **disponíveis para pronta-entrega** na mesma faixa de preço e com timbre excelente:
> * **Giannini GF-1R Aço Folk Sunburst** (mesma marca e acabamento Sunburst!) — **R$ 579,90** (ou **R$ 550,90 no PIX**) | *7 unidades em estoque*
> * **Yamaha F310 Aço Natural** — **R$ 699,90** (ou **R$ 664,90 no PIX**) | *14 unidades em estoque*
> * **Shelby SGD-195E Elétrico Aço Sunburst** (já vem com captação e afinador!) — **R$ 799,00** (ou **R$ 759,05 no PIX**) | *6 unidades em estoque*
> * **Tagima Woodstock Dreadnought Natural** — **R$ 899,00** (ou **R$ 854,05 no PIX**) | *11 unidades em estoque*
>
> Gostaria de conhecer melhor algum desses modelos disponíveis?

---

### Turno 2 — Produto Descontinuado e Recomendação de Equivalentes

**🧑 Cliente:**
> Entendi, obrigado pela sinceridade! E o violão 7 cordas Shelby SN-7C, vocês têm?

**🛠️ Ferramenta Acionada pelo Agente:**
* `search_products_catalog(query="Shelby SN-7C")`

**🎸 Assistente Empório da Música:**
> Verifiquei aqui e o **Shelby SN-7C 7 Cordas Nylon Natural** (R$ 749,00) foi **descontinuado** e não faz mais parte do nosso catálogo ativo.
>
> Porém, se você está buscando um **violão de 7 cordas** para choro, samba ou MPB, temos estas ótimas alternativas em estoque hoje:
> 1. **Tagima TW-7 7 Cordas Aço Natural** — **R$ 999,00** (ou **R$ 949,05 no PIX** | até 9x de R$ 111,00 sem juros) — *6 un. em estoque*
> 2. **Giannini GWNE-7 7 Cordas Nylon Natural** — **R$ 1.149,00** (ou **R$ 1.091,55 no PIX** | até 11x de R$ 104,45 sem juros) — *4 un. em estoque*
> 3. **Rozini RV-174 7 Cordas Nylon Natural** — **R$ 1.299,00** (ou **R$ 1.234,05 no PIX** | até 12x de R$ 108,25 sem juros) — *5 un. em estoque*
> 4. **Rozini RV-175 7 Cordas Elétrico Natural** (com tampo sólido e captação) — **R$ 1.699,00** (ou **R$ 1.614,05 no PIX**) — *3 un. em estoque*
>
> Se você buscava o Shelby por ser de **nylon**, o **Giannini GWNE-7** e o **Rozini RV-174** são referências tradicionais brasileiras no choro! Quer que eu simule as parcelas de algum deles para você?
