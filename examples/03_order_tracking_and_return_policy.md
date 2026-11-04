# Exemplo 3: Consulta de Pedido em Tempo Real e Aplicação das Políticas de Devolução/Troca

**Cenário:** A cliente **Letícia Gonçalves Rocha** consulta seu pedido (`#7`) e pergunta se pode devolver por arrependimento ou trocar caso apresente defeito, exigindo cruzamento entre os dados reais de `orders.csv` e as Seções 4.1, 4.2, 4.3 e 8.1 do Manual de Políticas.

---

### Turno 1 — Rastreamento e Solicitação de Devolução por Arrependimento

**🧑 Cliente:**
> Olá, meu nome é Letícia Gonçalves Rocha. Comprei um ukulele com vocês no pedido #7 e me arrependi da compra. Ainda posso devolver meu pedido?

**🛠️ Ferramentas Acionadas pelo Agente:**
* `lookup_customer_order(order_id=7, customer_identifier="Letícia Gonçalves Rocha")`
* `consult_store_policies(question="direito de arrependimento devolução prazo condições reembolso frete")`

**🎸 Assistente Empório da Música:**
> Olá, Letícia! Tudo bem? 🎶 Localizei o seu **Pedido #7** aqui no sistema:
> * **Produto:** 1x *Shelby SU-21S Soprano Sunburst*
> * **Valor Total:** R$ 159,90 (pago no cartão de crédito em 3x)
> * **Data do Pedido:** 03/02/2026
> * **Status:** Entregue (`delivered`) em **17/02/2026** (Código de rastreio: `BRKR1122334BR`)
>
> Sobre a **devolução por Direito de Arrependimento** (Seção 4.1 das nossas políticas e CDC):
> * O prazo para solicitar a devolução por arrependimento em compras online ou trocar por preferência (cor/modelo) é de até **7 (sete) dias corridos após a data de recebimento do produto**.
> * **Caso você esteja dentro dos 7 dias corridos do recebimento:** você pode devolver sem precisar de justificativa! Basta que o ukulele esteja na **embalagem original, sem sinais de uso e com todos os manuais**. Nesse caso, o **frete de devolução é totalmente por conta da Empório da Música** e o reembolso de R$ 159,90 é feito no seu cartão de crédito em até **10 dias úteis**.
> * **Caso já tenham se passado mais de 7 dias corridos desde a entrega (17/02/2026):** o prazo legal para devolução por arrependimento ou troca por preferência infelizmente já se encerrou.
>
> Aconteceu algum problema técnico ou defeito com o seu ukulele Shelby, ou você apenas gostaria de um modelo diferente (como um tamanho Concert ou Tenor)?

---

### Turno 2 — Dúvida sobre Defeito de Fabricação e Garantia

**🧑 Cliente:**
> Na verdade achei que uma tarraxa está prendendo um pouco desde que chegou. Se for defeito de fabricação, qual é o meu prazo?

**🛠️ Ferramenta Acionada pelo Agente:**
* `consult_store_policies(question="trocas por defeito de fabricação prazo garantia legal 30 dias 90 dias")`

**🎸 Assistente Empório da Música:**
> Ah, se for **defeito de fabricação** na tarraxa, a regra é diferente e bem mais ampla, Letícia! Olha só como você está protegida pelas nossas políticas (Seções 4.2 e 8.1):
>
> 1. **Até 30 dias corridos após a compra (Troca Direta na Loja):** Produtos com defeito de fabricação podem ser trocados diretamente conosco em até **30 dias corridos**.
> 2. **Até 90 dias corridos após o recebimento (Garantia Legal CDC):** Todos os instrumentos contam com **90 dias de garantia legal** contra defeitos de fabricação contados da data de entrega (17/02/2026), além da garantia do fabricante (que varia de 6 meses a 2 anos conforme o certificado). Após os primeiros 30 dias, o acionamento é feito junto ao fabricante, mas a **Empório da Música pode intermediar todo o processo para você** mediante solicitação!
>
> *(Lembrando apenas que a garantia cobre defeitos de fabricação, não cobrindo danos por queda, mau uso, umidade excessiva ou desgaste natural de cordas/trastes).*
>
> Como você é aqui de **Campo Grande/MS**, você pode trazer o seu ukulele até a nossa loja na **Rua 14 de Maio, 3200 - Centro** (Seg a Sex das 09h às 18h, Sáb das 09h às 13h) com a embalagem e certificado, ou me confirmar por aqui que já registro o seu atendimento para nossa equipe técnica avaliar a tarraxa! Prefere trazer na loja ou que eu abra o chamado por aqui?
