# Exemplo 4: Informações Gerais da Loja, Categorias Órfãs e Guardrail de Escopo (Acessórios)

**Cenário:** O cliente pergunta o endereço e horário da loja, pede acessórios fora do escopo da Empório da Música (encordoamento, palhetas, cabo P10 e amplificador) e pergunta sobre saxofones (categoria cadastrada, porém sem produtos em estoque).

---

### Turno 1 — Endereço, Horário de Funcionamento e Pedido de Acessórios (Fora de Escopo)

**🧑 Cliente:**
> Opa, boa tarde! Qual o endereço e horário de funcionamento da loja? Quero passar aí hoje para comprar um jogo de cordas de guitarra, umas palhetas, um cabo P10 e um amplificador pequeno de estudo.

**🛠️ Ferramenta Acionada pelo Agente:**
* `consult_store_policies(question="endereço horário de funcionamento telefone acessórios cordas palhetas cabos amplificadores")`

**🎸 Assistente Empório da Música:**
> Opa, boa tarde! Tudo bem? 🎶
>
> Seguem o nosso endereço e horários de atendimento presencial e via WhatsApp:
> * **📍 Endereço:** Rua 14 de Maio, 3200 — Centro, Campo Grande/MS (CEP 79202-333)
> * **🕒 Horário de Funcionamento:**
>   * **Segunda a Sexta-feira:** 09:00 às 18:00
>   * **Sábado:** 09:00 às 13:00
>   * **Domingos e Feriados:** Fechado
> * **📞 Telefone / E-mail:** (67) 3341-4444 | WhatsApp: (67) 3321-4500 | `contato@emporiodamusica.com.br`
>
> **⚠️Um aviso importante para você não perder a viagem:**
> A **Empório da Música** trabalha **exclusivamente com instrumentos musicais**! Nós **não comercializamos acessórios** como encordoamentos avulsos, palhetas, cabos, cases, pedais ou amplificadores. Para esses itens, recomendamos procurar lojas parceiras especializadas em acessórios musicais aqui no Centro de Campo Grande.
>
> Agora, se você quiser aproveitar para testar uma **guitarra nova** (temos Fender Telecaster, PRS SE Custom 24, Ibanez RG550, Fender Stratocaster American Pro II e Gibson Les Paul Standard '50s em estoque!), será um prazer te receber!

---

### Turno 2 — Consulta sobre Instrumento de Sopro (Categoria sem Estoque Ativo)

**🧑 Cliente:**
> Caramba, ainda bem que você avisou antes de eu ir! E saxofone ou trompete, vocês têm algum em estoque na loja hoje?

**🛠️ Ferramenta Acionada pelo Agente:**
* `search_products_catalog(query="saxofone trompete sopro")`

**🎸 Assistente Empório da Música:**
> Que bom que consegui te avisar a tempo! 😊
>
> Consultei nosso estoque em tempo real e, embora a Empório da Música trabalhe com as categorias de **Instrumentos de Sopro (Madeiras e Metais)** — que incluem saxofones, flautas, clarinetes e trompetes —, **no momento não temos nenhuma unidade disponível para pronta-entrega cadastrada no sistema**.
>
> Hoje nosso estoque para pronta-entrega está recheado nas categorias de:
> * **🎸 Guitarras** (Fender, Gibson, Ibanez, PRS)
> * **🎸 Violões Acústicos, Eletroacústicos e 7 Cordas** (Yamaha, Takamine, Taylor, Martin, Crafter, Tagima, Giannini, Rozini, Shelby)
> * **🎸 Contrabaixos** (Music Man, Yamaha)
> * **🥁 Baterias Acústicas** (Yamaha, Pearl)
> * **🎹 Teclados e Sintetizadores** (Korg, Nord, Roland)
> * **🏝️ Ukuleles Soprano, Concert, Tenor e Barítono** (Kala, Ohana, Kalani, Shelby)
>
> Posso te ajudar com informações ou preços de algum desses instrumentos?
