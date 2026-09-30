import { BrowserRouter, Outlet, Route, Routes } from "react-router";

import { ComBarra } from "./components/BarraNavegacao";
import { RotaProtegida, RotaSoParaVisitante } from "./components/Rotas";
import { AuthProvider } from "./contexts/AuthContext";
import { VeiculosProvider } from "./contexts/VeiculosContext";
import CadastroPage from "./pages/CadastroPage";
import ContaPage from "./pages/ContaPage";
import EmBrevePage from "./pages/EmBrevePage";
import EsqueciSenhaPage from "./pages/EsqueciSenhaPage";
import FotoDetalhePage from "./pages/FotoDetalhePage";
import FotoNovaPage from "./pages/FotoNovaPage";
import FotosPage from "./pages/FotosPage";
import InicioPage from "./pages/InicioPage";
import LoginPage from "./pages/LoginPage";
import MaisPage from "./pages/MaisPage";
import NaoEncontradaPage from "./pages/NaoEncontradaPage";
import QuilometragemPage from "./pages/QuilometragemPage";
import RedefinirSenhaPage from "./pages/RedefinirSenhaPage";
import SituacaoSistemaPage from "./pages/SituacaoSistemaPage";
import VeiculoDetalhePage from "./pages/VeiculoDetalhePage";
import { EditarVeiculoPage, NovoVeiculoPage } from "./pages/VeiculoFormPage";
import VeiculosPage from "./pages/VeiculosPage";

/** Tudo o que exige login. A lista de veículos só existe aqui dentro. */
function AreaLogada() {
  return (
    <RotaProtegida>
      <VeiculosProvider>
        <Outlet />
      </VeiculosProvider>
    </RotaProtegida>
  );
}

/** Endereços do app. Separado do App para os testes usarem um roteador em memória. */
export function RotasDoApp() {
  return (
    <Routes>
      <Route element={<AreaLogada />}>
        {/* Telas com a barra de navegação inferior */}
        <Route element={<ComBarra />}>
          <Route path="/" element={<InicioPage />} />
          <Route path="/manutencao" element={
            <EmBrevePage titulo="Manutenção" etapa={4}
              descricao="Aqui ficarão as manutenções pendentes, as realizadas e os planos." />
          } />
          <Route path="/diagnostico" element={
            <EmBrevePage titulo="Diagnóstico" etapa={5}
              descricao="Aqui ficarão os problemas registrados, com anotações e fotos." />
          } />
          <Route path="/financas" element={
            <EmBrevePage titulo="Finanças" etapa={6}
              descricao="Aqui ficarão os gastos do mês e, na etapa 7, os abastecimentos e o consumo." />
          } />
          <Route path="/mais" element={<MaisPage />} />
          <Route path="/conta" element={<ContaPage />} />
          <Route path="/veiculos" element={<VeiculosPage />} />
          <Route path="/veiculos/:veiculoId" element={<VeiculoDetalhePage />} />
          <Route path="/veiculos/:veiculoId/km" element={<QuilometragemPage />} />
          <Route path="/veiculos/:veiculoId/fotos" element={<FotosPage />} />
          <Route path="/veiculos/:veiculoId/fotos/:fotoId" element={<FotoDetalhePage />} />
        </Route>
        {/* Formulários em tela cheia, sem a barra (como no PDF) */}
        <Route path="/veiculos/novo" element={<NovoVeiculoPage />} />
        <Route path="/veiculos/:veiculoId/editar" element={<EditarVeiculoPage />} />
        <Route path="/veiculos/:veiculoId/fotos/nova" element={<FotoNovaPage />} />
      </Route>
      <Route path="/entrar" element={<RotaSoParaVisitante><LoginPage /></RotaSoParaVisitante>} />
      <Route path="/criar-conta" element={<RotaSoParaVisitante><CadastroPage /></RotaSoParaVisitante>} />
      <Route path="/esqueci-senha" element={<EsqueciSenhaPage />} />
      <Route path="/redefinir-senha" element={<RedefinirSenhaPage />} />
      <Route path="/situacao" element={<SituacaoSistemaPage />} />
      <Route path="*" element={<NaoEncontradaPage />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <RotasDoApp />
      </AuthProvider>
    </BrowserRouter>
  );
}
