"""
Triple Pattern Fragments client

http://www.hydra-cg.com/spec/latest/triple-pattern-fragments/
"""
import logging
from rdflib import Namespace, RDF
from rdflib.plugin import register, Store

from hydra import Collection, HYDRA, NULL

LOG = logging.getLogger(__name__)

VOID = Namespace('http://rdfs.org/ns/void#')

class TriplePatternFragment(Collection):

    def iter_triples(self):
        for p in self.pages:
            for triple in p.graph.default_context:
                yield triple
    triples = property(iter_triples)

    def get_triple_count(self):
        return self.graph \
            .value(self.identifier, VOID.triples, default=NULL).toPython()
    triple_count = property(get_triple_count)

    def get_dataset(self, headers=None, http=None):
        graph = self.graph
        for candidate in graph.subjects(VOID.subset, self.identifier):
            if (candidate, HYDRA.search, None) in graph:
                return TPFAwareCollection(graph, candidate)
        return None
    dataset = property(get_dataset)


class TPFAwareCollection(Collection):

    triple_search = None

    def get_tpf(self, subject=None, predicate=None, object=None, headers=None, http=None):
        if self.triple_search is None:
            self.triple_search = self.find_suitable_template([
                    RDF.subject, RDF.predicate, RDF.object])
            if self.triple_search is None:
                raise ValueError("Couldn't find any TPF search template")
        tpf_iri = self.triple_search.generate_iri({
            RDF.subject: subject,
            RDF.predicate: predicate,
            RDF.object: object,
        }, default_representation=HYDRA.ExplicitRepresentation)
        return TriplePatternFragment.from_iri(tpf_iri, headers, http)

    def iter_triples(self, subject=None, predicate=None, object=None):
        return self.get_tpf(subject, predicate, object).iter_triples()


class TPFStore(Store):

    def open(self, start_iri, create=False):
        self.collec = TriplePatternFragment.from_iri(start_iri).dataset

    def add(self, tuple, context, quoted=False):
        subject, predicate, object =tuple
        raise NotImplemented("TPFStore is readonly")

    def remove(self, tuple, context=None):
        subject, predicate, object =tuple
        raise NotImplemented("TPFStore is readonly")

    def triples(self, triple_pattern, context=None):
        for triple in self.collec.iter_triples(*triple_pattern):
            yield triple, context

    def __len__(self, context=None):
        return self.collec.get_tpf().triple_count

register("TPFStore", Store, "tpf", "TPFStore")