# Corpus analysis

The RDF dataset of Zeri is available [here](https://github.com/marilenadaquino/mauth/blob/master/data/zeri/FINAL_zeri.nq)

### Zeri dataset
**Q1** retrieves:
 * all the criteria supporting accepted attributions `?critLabel`
 * the counting of accepted criteria `?count` over the discarded ones `?otherLabel`

#### Q1.
~~~~
SELECT ?critLabel (count(DISTINCT ?artwork) As ?count) ?otherLabel

WHERE { ?artwork <http://www.cidoc-crm.org/cidoc-crm/P94i_was_created_by> ?creation ; 
                 <http://www.cidoc-crm.org/cidoc-crm/P94i_was_created_by> ?creationX .
       
  		?creation <http://www.w3.org/ns/prov#wasGeneratedBy> ?accepted . 
        ?creationX <http://www.w3.org/ns/prov#wasGeneratedBy> ?discarded .
  
  		?accepted <http://purl.org/emmedi/hico/hasInterpretationType> <http://purl.org/emmedi/mauth/zeri/zeri-preferred-attribution> ;
        		<http://purl.org/emmedi/hico/hasInterpretationCriterion> ?crit . 
		
  		?discarded <http://purl.org/emmedi/hico/hasInterpretationType>	<http://purl.org/emmedi/mauth/zeri/zeri-discarded-attribution> ;
				<http://purl.org/emmedi/hico/hasInterpretationCriterion> ?other . 
     
       ?crit rdfs:label ?critLabel . ?other rdfs:label ?otherLabel .
       FILTER (?creation != ?creationX) .}
GROUP BY ?critLabel ?otherLabel
ORDER BY ?critLabel DESC(?count)
~~~~

Results are shown in `zeri_comparison.csv`.


### I Tatti dataset

The RDF dataset of I Tatti is available [here](https://github.com/marilenadaquino/mauth/blob/master/data/itatti/FINAL_itatti.nq)

**Q2** retrieves:
 * all the criteria supporting accepted attributions `?critLabel`
 * the counting of accepted criteria `?count` over the discarded ones `?otherLabel`

#### Q2.
~~~~
SELECT ?critLabel (count(DISTINCT ?artwork) As ?count) ?otherLabel

WHERE { ?artwork <http://www.cidoc-crm.org/cidoc-crm/P94i_was_created_by> ?creation ; 
                 <http://www.cidoc-crm.org/cidoc-crm/P94i_was_created_by> ?creationX .
       
  		?creation <http://www.w3.org/ns/prov#wasGeneratedBy> ?accepted . 
        ?creationX <http://www.w3.org/ns/prov#wasGeneratedBy> ?discarded .
  
  		?accepted <http://purl.org/emmedi/hico/hasInterpretationType> <http://purl.org/emmedi/mauth/itatti/itatti-preferred-attribution> ;
        		<http://purl.org/emmedi/hico/hasInterpretationCriterion> ?crit . 
		
  		?discarded <http://purl.org/emmedi/hico/hasInterpretationType>	<http://purl.org/emmedi/mauth/itatti/itatti-discarded-attribution> ;
				<http://purl.org/emmedi/hico/hasInterpretationCriterion> ?other . 
     
       ?crit rdfs:label ?critLabel . ?other rdfs:label ?otherLabel .
       FILTER (?creation != ?creationX) .}
GROUP BY ?critLabel ?otherLabel
ORDER BY ?critLabel DESC(?count)
~~~~

Results are shown in `itatti_comparison.csv`.

### Frick dataset

The RDF dataset of Frick is available [here](https://github.com/marilenadaquino/mauth/blob/master/data/frick/FINAL_frick.nq)

**Q3** retrieves:
 * all the criteria supporting accepted attributions `?critLabel`
 * the counting of accepted criteria `?count` over the discarded ones `?otherLabel`

#### Q3.
~~~~
SELECT ?critLabel (count(DISTINCT ?artwork) As ?count) ?otherLabel

WHERE { ?artwork <http://www.cidoc-crm.org/cidoc-crm/P94i_was_created_by> ?creation ; 
                 <http://www.cidoc-crm.org/cidoc-crm/P94i_was_created_by> ?creationX .
       
  		?creation <http://www.w3.org/ns/prov#wasGeneratedBy> ?accepted . 
        ?creationX <http://www.w3.org/ns/prov#wasGeneratedBy> ?discarded .
  
  		?accepted <http://purl.org/emmedi/hico/hasInterpretationType> <http://purl.org/emmedi/mauth/frick/frick-preferred-attribution> ;
        		<http://purl.org/emmedi/hico/hasInterpretationCriterion> ?crit . 
		
  		?discarded <http://purl.org/emmedi/hico/hasInterpretationType>	<http://purl.org/emmedi/mauth/frick/frick-discarded-attribution> ;
				<http://purl.org/emmedi/hico/hasInterpretationCriterion> ?other . 
     
       ?crit rdfs:label ?critLabel . ?other rdfs:label ?otherLabel .
       FILTER (?creation != ?creationX) .}
GROUP BY ?critLabel ?otherLabel
ORDER BY ?critLabel DESC(?count)
~~~~

Results are shown in `frick_comparison.csv`.