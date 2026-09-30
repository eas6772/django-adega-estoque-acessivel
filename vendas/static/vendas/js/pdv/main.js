// Orquestra os módulos da frente de caixa (C1-C8). Cada módulo cuida de uma
// responsabilidade só; este arquivo apenas os liga entre si.
import * as carrinho from './carrinho.js';
import * as busca from './busca.js';
import { selecionarProduto } from './dialogo-lote.js';
import * as finalizar from './finalizar.js';
import * as atalhos from './atalhos.js';

carrinho.init();
busca.init(selecionarProduto);
finalizar.init();
atalhos.init();
